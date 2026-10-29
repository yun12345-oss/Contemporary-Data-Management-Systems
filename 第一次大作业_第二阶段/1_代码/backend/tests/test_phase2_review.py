from copy import deepcopy

import pytest
from test_phase2 import (
    allow_repeat,
    content,
    grant,
    imp,
    new,
    ok,
    publish,
    submit,
    survey,
)
from test_phase2 import (
    other as other,
)


@pytest.mark.parametrize(
    "bounds",
    [
        ["0", "inf"],
        ["-inf", "100"],
        ["0", "nan"],
        ["0", "10000000000000000"],
        ["-10000000000000000", "100"],
        ["0", "1e400"],
        ["0", "-inf"],
    ],
)
def test_unsafe_histogram_boundaries_rejected_before_aggregation(
    client, database, monkeypatch, bounds
):
    q = new(client)
    original = type(database.responses).aggregate

    def guarded(self, *args, **kwargs):
        assert self.name != "responses", "unsafe input reached response aggregation"
        return original(self, *args, **kwargs)

    monkeypatch.setattr(type(database.responses), "aggregate", guarded)
    r = client.get(
        f"/api/question-versions/{q['version']['_id']}/statistics",
        params=[("boundaries", b) for b in bounds],
    )
    assert r.status_code == 422, r.text
    assert "有限数值" in r.json()["error"]


@pytest.mark.parametrize(
    "bounds", [["0", "100"], ["-1000000000000000", "1000000000000000"]]
)
def test_safe_histogram_boundaries_including_limits(client, bounds):
    q = new(client)
    result = ok(
        client.get(
            f"/api/question-versions/{q['version']['_id']}/statistics",
            params=[("boundaries", b) for b in bounds],
        )
    )
    assert (
        result["valid_answers"] == 0
        and sum(x["count"] for x in result["distribution"]) == 0
    )


def test_explicit_empty_boundaries_are_not_replaced_with_defaults(client, database):
    from app.errors import BusinessError
    from app.services.question_statistics import aggregate

    q = new(client)
    user = database.users.find_one({"_id": q["question"]["owner_id"]})
    with pytest.raises(BusinessError, match="分组边界需严格递增"):
        aggregate(database, user, q["version"]["_id"], boundaries=[])


def test_statistics_only_grantee_has_scoped_access_without_question_use(client, other):
    q = new(client)
    s = publish(client, allow_repeat(client, imp(client, survey(client), q["version"])))
    submit(client, s, {s["draft"]["questions"][0]["id"]: "27"})
    g = grant(client, other, q["version"], "aggregate", s["_id"])
    assert ok(other.get("/api/questions"))["total"] == 0
    records = ok(other.get("/api/grants"))["items"]
    assert records[0]["_id"] == g["_id"] and records[0]["kind"] == "aggregate"
    result = ok(
        other.get(
            f"/api/question-versions/{q['version']['_id']}/statistics",
            params={"survey_id": s["_id"]},
        )
    )
    assert result["average"] == 27
    assert other.get(f"/api/questions/{q['question']['_id']}").status_code == 404
    ok(client.post(f"/api/grants/{g['_id']}/revoke", json={"revision": 1}))
    assert (
        other.get(
            f"/api/question-versions/{q['version']['_id']}/statistics",
            params={"survey_id": s["_id"]},
        ).status_code
        == 403
    )


def test_shared_recipient_usage_is_available_without_owner_history(client, other):
    q = new(client)
    grant(client, other, q["version"])
    imported = imp(other, survey(other), q["version"])
    owner_survey = imp(client, survey(client), q["version"])
    assert other.get(f"/api/questions/{q['question']['_id']}").status_code == 404
    usage = ok(other.get(f"/api/questions/{q['question']['_id']}/usage"))
    assert (
        usage["used_surveys"] == 1 and usage["items"][0]["survey_id"] == imported["_id"]
    )
    assert owner_survey["_id"] not in str(usage)


def test_twenty_first_library_available_on_second_page(client):
    ids = {
        ok(client.post("/api/libraries", json={"name": f"库{i:02d}"}), 201)["_id"]
        for i in range(21)
    }
    first = ok(client.get("/api/libraries"))
    second = ok(client.get("/api/libraries?page=2"))
    assert first["total"] == second["total"] == 21
    assert len(first["items"]) == 20 and len(second["items"]) == 1
    assert {x["_id"] for x in first["items"] + second["items"]} == ids


def test_library_search_filters_fixed_versions_before_pagination(client):
    q = new(client)
    lid = ok(client.post("/api/libraries", json={"name": "跨页检索"}), 201)["_id"]
    for i in range(21):
        if i:
            c = deepcopy(content())
            c["title"] = "唯一目标 [x]" if i == 20 else f"普通{i}"
            q = ok(
                client.post(
                    f"/api/questions/{q['question']['_id']}/versions",
                    json={
                        "revision": q["question"]["revision"],
                        "parent_version_id": q["version"]["_id"],
                        "content": c,
                    },
                ),
                201,
            )
        ok(
            client.post(
                f"/api/libraries/{lid}/items",
                json={
                    "revision": i + 1,
                    "question_version_id": q["version"]["_id"],
                    "position": i,
                },
            ),
            201,
        )
    first = ok(client.get(f"/api/libraries/{lid}/items"))
    assert first["total"] == 21 and len(first["items"]) == 20
    filtered = ok(
        client.get(
            f"/api/libraries/{lid}/items",
            params={"search": "[x]", "question_id": q["question"]["_id"]},
        )
    )
    assert filtered["total"] == 1 and len(filtered["items"]) == 1
    assert filtered["items"][0]["version"]["content"]["title"] == "唯一目标 [x]"
    assert (
        ok(
            client.get(
                f"/api/libraries/{lid}/items", params={"search": "[x]", "page": 2}
            )
        )["items"]
        == []
    )
    assert (
        ok(
            client.get(
                f"/api/libraries/{lid}/items",
                params={"search": "[x]", "question_id": "wrong"},
            )
        )["total"]
        == 0
    )


def test_library_search_does_not_leak_revoked_private_title(client, other):
    q = new(client)
    g = grant(client, other, q["version"])
    lid = ok(other.post("/api/libraries", json={"name": "共享检索"}), 201)["_id"]
    ok(
        other.post(
            f"/api/libraries/{lid}/items",
            json={"revision": 1, "question_version_id": q["version"]["_id"]},
        ),
        201,
    )
    assert ok(other.get(f"/api/libraries/{lid}/items?search=年龄"))["total"] == 1
    ok(client.post(f"/api/grants/{g['_id']}/revoke", json={"revision": 1}))
    assert ok(other.get(f"/api/libraries/{lid}/items?search=年龄"))["total"] == 0
    plain = ok(other.get(f"/api/libraries/{lid}/items"))
    assert plain["total"] == 1 and plain["items"][0]["version"] is None
    assert client.get(f"/api/libraries/{lid}/items?search=年龄").status_code == 404
