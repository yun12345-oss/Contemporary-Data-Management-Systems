"""Real MongoDB tests for provenance, authorization, versioning and regression."""

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier, Event
from uuid import uuid4

import pytest
from app.config import ROOT
from app.database import initialize
from app.main import create_app
from app.migration import rollback, upgrade
from app.services import questions
from fastapi.testclient import TestClient
from pymongo.errors import WriteError


def ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


@pytest.fixture
def other(client, app):
    c = TestClient(app)
    u = ok(
        c.post(
            "/api/auth/register",
            json={"username": "peer_" + uuid4().hex[:10], "password": "TestPass123!"},
        ),
        201,
    )
    c.account = u
    yield c
    c.close()


def content(kind="number"):
    c = {
        "type": kind,
        "title": "年龄",
        "options": [],
        "validation": {"min": 0, "max": 120, "integer_only": True},
    }
    if kind in ("single_choice", "multiple_choice"):
        c.update(
            title="工具",
            options=[
                {"id": "a", "label": "A"},
                {"id": "b", "label": "B"},
                {"id": "c", "label": "C"},
            ],
            validation={},
        )
    return c


def new(client, kind="number"):
    return ok(client.post("/api/questions", json={"content": content(kind)}), 201)


def survey(client):
    return ok(client.post("/api/surveys", json={"title": "来源测试"}), 201)


def imp(client, s, v):
    return ok(
        client.post(
            f"/api/surveys/{s['_id']}/questions/import",
            json={"revision": s["revision"], "question_version_id": v["_id"]},
        )
    )


def save(client, s):
    return client.put(
        f"/api/surveys/{s['_id']}/draft",
        json={"revision": s["revision"], "draft": s["draft"]},
    )


def publish(client, s):
    ok(
        client.post(
            f"/api/surveys/{s['_id']}/publish", json={"revision": s["revision"]}
        )
    )
    return ok(client.get(f"/api/surveys/{s['_id']}"))


def submit(client, s, answers):
    a = ok(
        client.post(f"/api/public/{s['share_code']}/attempt", json={"anonymous": True})
    )
    a = ok(
        client.put(
            f"/api/attempts/{a['_id']}",
            json={"revision": a["revision"], "answers": answers},
        )
    )
    return ok(
        client.post(
            f"/api/attempts/{a['_id']}/submit", json={"revision": a["revision"]}
        )
    )


def allow_repeat(client, s):
    s["draft"]["allow_repeat"] = True
    s["draft"]["allow_anonymous"] = True
    return ok(save(client, s))


def grant(client, other, v, kind="use", sid=None):
    return ok(
        client.post(
            "/api/grants",
            json={
                "kind": kind,
                "question_version_id": v["_id"],
                "username": other.account["username"],
                "survey_id": sid,
            },
        ),
        201,
    )


def newer(client, q, base=None, title="成年年龄"):
    c = deepcopy(q["version"]["content"])
    c["title"] = title
    return ok(
        client.post(
            f"/api/questions/{q['question']['_id']}/versions",
            json={
                "revision": q["question"]["revision"],
                "parent_version_id": base or q["version"]["_id"],
                "content": c,
                "change_note": title,
            },
        ),
        201,
    )


def test_versions_branch_restore_and_immutable_snapshot(client, database):
    a = new(client)
    b = newer(client, a)
    c = newer(client, b, base=a["version"]["_id"], title="分支")
    r = ok(
        client.post(
            f"/api/questions/{a['question']['_id']}/restore",
            json={
                "revision": c["question"]["revision"],
                "parent_version_id": c["version"]["_id"],
                "restored_from_version_id": a["version"]["_id"],
            },
        ),
        201,
    )
    assert r["version"]["version"] == 4
    assert r["version"]["parent_version_id"] == c["version"]["_id"]
    assert r["version"]["restored_from_version_id"] == a["version"]["_id"]
    assert r["version"]["content"] == a["version"]["content"]
    assert (
        database.question_versions.find_one({"_id": a["version"]["_id"]})["content"]
        == a["version"]["content"]
    )
    assert (
        len(
            ok(
                client.get(
                    f"/api/question-versions/{a['version']['_id']}/diff/{b['version']['_id']}"
                )
            )
        )
        == 1
    )


def test_concurrent_version_allocation_one_revision(client, app, database):
    a = new(client)
    barrier = Barrier(2)

    def work(i):
        c = TestClient(app)
        c.cookies.update(client.cookies)
        barrier.wait()
        r = c.post(
            f"/api/questions/{a['question']['_id']}/versions",
            json={
                "revision": 1,
                "parent_version_id": a["version"]["_id"],
                "content": {**content(), "title": str(i)},
            },
        )
        c.close()
        return r.status_code

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(work, range(2)))
    assert sorted(results) == [201, 409]
    assert sorted(
        v["version"]
        for v in database.question_versions.find({"question_id": a["question"]["_id"]})
    ) == [1, 2]


def test_version_failure_rolls_back_sequence(client, database, monkeypatch):
    a = new(client)
    before = database.questions.find_one({"_id": a["question"]["_id"]})
    collection = database.question_versions

    def fail(*args, **kwargs):
        raise RuntimeError("injected insert failure")

    # Patch Collection class, limited to version inserts.
    original = type(collection).insert_one

    def insert(self, *args, **kwargs):
        if self.name == "question_versions":
            return fail()
        return original(self, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(type(collection), "insert_one", insert)
        with pytest.raises(RuntimeError):
            newer(client, a)
    assert database.questions.find_one({"_id": a["question"]["_id"]}) == before


@pytest.mark.parametrize(
    "field",
    [
        "version",
        "question_version_id",
        "survey_id",
        "instance_id",
        "imported_by",
        "imported_at",
        "grant_id",
    ],
)
def test_source_credentials_cannot_be_forged(client, field):
    a = new(client)
    s = imp(client, survey(client), a["version"])
    bad = deepcopy(s)
    bad["draft"]["questions"][0]["source"][field] = (
        99
        if field == "version"
        else ("2026-01-01T00:00:00Z" if field == "imported_at" else "forged")
    )
    assert save(client, bad).status_code == 403
    assert ok(client.get(f"/api/surveys/{s['_id']}"))["revision"] == s["revision"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "伪造"),
        ("type", "text"),
        ("options", [{"id": "x", "label": "x"}]),
        ("validation", {"max": 90}),
    ],
)
def test_content_cannot_change_under_old_source(client, field, value):
    a = new(client)
    s = imp(client, survey(client), a["version"])
    s["draft"]["questions"][0][field] = value
    assert save(client, s).status_code == 403


def test_source_removal_copy_and_duplicate_id_rejected(client):
    a = new(client)
    s = imp(client, survey(client), a["version"])
    bad = deepcopy(s)
    bad["draft"]["questions"][0].pop("source")
    assert save(client, bad).status_code == 403
    bad = deepcopy(s)
    copy = deepcopy(bad["draft"]["questions"][0])
    copy["id"] = "copy"
    bad["draft"]["questions"].append(copy)
    assert save(client, bad).status_code == 403
    bad = deepcopy(s)
    bad["draft"]["questions"].append(deepcopy(bad["draft"]["questions"][0]))
    assert save(client, bad).status_code == 422
    other = survey(client)
    other["draft"]["questions"] = s["draft"]["questions"]
    assert save(client, other).status_code == 403


def test_import_ownership_instance_id_and_owner_detach(client):
    a = new(client)
    s = imp(client, survey(client), a["version"])
    s = imp(client, s, a["version"])
    assert len({q["id"] for q in s["draft"]["questions"]}) == 2
    s["draft"]["questions"][0]["required"] = False
    s = ok(save(client, s))
    iid = s["draft"]["questions"][0]["id"]
    s = ok(
        client.post(
            f"/api/surveys/{s['_id']}/questions/detach",
            json={"revision": s["revision"], "instance_id": iid},
        )
    )
    assert "source" not in s["draft"]["questions"][0]
    s["draft"]["questions"][0]["title"] = "独立内容"
    ok(save(client, s))


def test_exact_version_share_no_future_leak_or_privilege(client, other):
    a = new(client)
    grant(client, other, a["version"])
    b = newer(client, a, title="私密新版本标题")
    listed = ok(other.get("/api/questions"))
    assert len(listed["items"]) == 1 and listed["items"][0]["title"] == "年龄"
    assert len(listed["items"][0]["versions"]) == 1
    assert other.get(f"/api/question-versions/{b['version']['_id']}").status_code == 404
    assert ok(other.get("/api/questions?search=私密新版本标题"))["total"] == 0
    assert (
        other.post(
            "/api/grants",
            json={
                "kind": "use",
                "question_version_id": a["version"]["_id"],
                "username": ok(client.get("/api/auth/me"))["username"],
            },
        ).status_code
        == 404
    )
    assert (
        other.post(
            f"/api/questions/{a['question']['_id']}/versions",
            json={
                "revision": b["question"]["revision"],
                "parent_version_id": a["version"]["_id"],
                "content": content(),
            },
        ).status_code
        == 404
    )


def test_revoke_keeps_existing_draft_but_blocks_new_import_and_laundering(
    client, other
):
    a = new(client)
    g = grant(client, other, a["version"])
    s = imp(other, survey(other), a["version"])
    ok(client.post(f"/api/grants/{g['_id']}/revoke", json={"revision": g["revision"]}))
    iid = s["draft"]["questions"][0]["id"]
    for action in ["detach", "save-reusable"]:
        assert (
            other.post(
                f"/api/surveys/{s['_id']}/questions/{action}",
                json={"revision": s["revision"], "instance_id": iid},
            ).status_code
            == 404
        )
    assert (
        other.post(
            f"/api/surveys/{s['_id']}/questions/import",
            json={
                "revision": s["revision"],
                "question_version_id": a["version"]["_id"],
            },
        ).status_code
        == 403
    )
    bad = deepcopy(s)
    bad["draft"]["questions"][0].pop("source")
    assert save(other, bad).status_code == 403
    s = allow_repeat(other, s)
    s = publish(other, s)
    submit(other, s, {iid: "30"})
    assert ok(other.get(f"/api/surveys/{s['_id']}/statistics"))["total"] == 1


def test_archive_preserves_existing_blocks_import_and_versions(client):
    a = new(client)
    s = imp(client, survey(client), a["version"])
    ok(
        client.post(
            f"/api/questions/{a['question']['_id']}/archive", json={"revision": 1}
        )
    )
    assert (
        client.post(
            f"/api/surveys/{s['_id']}/questions/import",
            json={
                "revision": s["revision"],
                "question_version_id": a["version"]["_id"],
            },
        ).status_code
        == 409
    )
    publish(client, s)
    assert (
        client.post(
            f"/api/questions/{a['question']['_id']}/versions",
            json={
                "revision": 2,
                "parent_version_id": a["version"]["_id"],
                "content": content(),
            },
        ).status_code
        == 409
    )


@pytest.mark.parametrize("mode", ["revoke", "archive"])
def test_import_commits_before_concurrent_revoke_archive(
    client, other, app, database, monkeypatch, mode
):
    a = new(client)
    g = grant(client, other, a["version"])
    s = survey(other)
    entered, release = Event(), Event()
    original = questions.authorize_use
    first = [True]

    def paused(db, user, vid, session):
        result = original(db, user, vid, session)
        if first[0]:
            first[0] = False
            entered.set()
            assert release.wait(10)
        return result

    # Import writes are uncommitted; owner's conflicting update waits. Let import commit first.
    with monkeypatch.context() as m:
        m.setattr(questions, "authorize_use", paused)

        def do_import():
            c = TestClient(app)
            c.cookies.update(other.cookies)
            return c.post(
                f"/api/surveys/{s['_id']}/questions/import",
                json={
                    "revision": s["revision"],
                    "question_version_id": a["version"]["_id"],
                },
            )

        with ThreadPoolExecutor(2) as pool:
            task = pool.submit(do_import)
            assert entered.wait(10)

            def change():
                c = TestClient(app)
                c.cookies.update(client.cookies)
                path = (
                    f"/api/grants/{g['_id']}/revoke"
                    if mode == "revoke"
                    else f"/api/questions/{a['question']['_id']}/archive"
                )
                return c.post(path, json={"revision": 1})

            changing = pool.submit(change)
            release.set()
            assert task.result(timeout=15).status_code == 200
            assert changing.result(timeout=15).status_code == 200
    saved = ok(other.get(f"/api/surveys/{s['_id']}"))
    publish(other, saved)
    denied = other.post(
        f"/api/surveys/{s['_id']}/questions/import",
        json={
            "revision": saved["revision"] + 1,
            "question_version_id": a["version"]["_id"],
        },
    )
    assert denied.status_code in [403, 409]


@pytest.mark.parametrize("mode", ["revoke", "archive"])
def test_revoke_archive_commits_before_inflight_import(
    client, other, app, database, monkeypatch, mode
):
    a = new(client)
    g = grant(client, other, a["version"])
    s = survey(other)
    entered, release = Event(), Event()
    original = questions.authorize_use
    first = [True]

    def paused(db, user, vid, session):
        if first[0]:
            first[0] = False
            entered.set()
            assert release.wait(10)
        return original(db, user, vid, session)

    with monkeypatch.context() as m:
        m.setattr(questions, "authorize_use", paused)

        def do_import():
            c = TestClient(app)
            c.cookies.update(other.cookies)
            return c.post(
                f"/api/surveys/{s['_id']}/questions/import",
                json={
                    "revision": s["revision"],
                    "question_version_id": a["version"]["_id"],
                },
            )

        with ThreadPoolExecutor(1) as pool:
            task = pool.submit(do_import)
            assert entered.wait(10)
            path = (
                f"/api/grants/{g['_id']}/revoke"
                if mode == "revoke"
                else f"/api/questions/{a['question']['_id']}/archive"
            )
            ok(client.post(path, json={"revision": 1}))
            release.set()
            assert task.result(timeout=15).status_code in [403, 409]
    stored = database.surveys.find_one({"_id": s["_id"]})
    assert not stored["draft"]["questions"] and stored["revision"] == 1


def test_filler_does_not_receive_import_credentials(client):
    a = new(client)
    s = publish(client, allow_repeat(client, imp(client, survey(client), a["version"])))
    attempt = ok(
        client.post(f"/api/public/{s['share_code']}/attempt", json={"anonymous": True})
    )
    assert "source" not in attempt["definition"]["questions"][0]
    assert ok(client.get(f"/api/surveys/{s['_id']}"))["draft"]["questions"][0]["source"]


def test_upgrade_invalid_rules_saved_then_repaired_snapshot_untouched(client, database):
    a = new(client, "single_choice")
    s = imp(client, survey(client), a["version"])
    iid = s["draft"]["questions"][0]["id"]
    q = s["draft"]["questions"][0]
    q["routing"] = {
        "rules": [
            {
                "condition": {"question_id": iid, "operator": "eq", "value": "c"},
                "target": "END",
            }
        ],
        "default_target": None,
    }
    s = ok(save(client, s))
    s = publish(client, s)
    old = database.survey_versions.find_one({"survey_id": s["_id"], "version": 1})
    c = deepcopy(a["version"]["content"])
    c["options"] = c["options"][:2]
    b = ok(
        client.post(
            f"/api/questions/{a['question']['_id']}/versions",
            json={
                "revision": 1,
                "parent_version_id": a["version"]["_id"],
                "content": c,
            },
        ),
        201,
    )
    body = {
        "revision": s["revision"],
        "instance_id": iid,
        "question_version_id": b["version"]["_id"],
    }
    preview = ok(
        client.post(f"/api/surveys/{s['_id']}/questions/upgrade-preview", json=body)
    )
    assert preview["issues"]
    s = ok(client.post(f"/api/surveys/{s['_id']}/questions/upgrade", json=body))
    assert s["draft_issues"]
    assert (
        client.post(
            f"/api/surveys/{s['_id']}/publish", json={"revision": s["revision"]}
        ).status_code
        == 422
    )
    s = ok(save(client, s))
    s["draft"]["questions"][0]["routing"]["rules"] = []
    s = ok(save(client, s))
    assert not s["draft_issues"]
    publish(client, s)
    assert database.survey_versions.find_one({"_id": old["_id"]}) == old


def test_old_attempt_remains_pinned_after_question_upgrade(client, database):
    a = new(client)
    s = publish(client, allow_repeat(client, imp(client, survey(client), a["version"])))
    iid = s["draft"]["questions"][0]["id"]
    attempt = ok(
        client.post(f"/api/public/{s['share_code']}/attempt", json={"anonymous": True})
    )
    b = newer(client, a)
    s = ok(
        client.post(
            f"/api/surveys/{s['_id']}/questions/upgrade",
            json={
                "revision": s["revision"],
                "instance_id": iid,
                "question_version_id": b["version"]["_id"],
            },
        )
    )
    publish(client, s)
    restored = ok(client.get(f"/api/attempts/{attempt['_id']}"))
    assert restored["definition"]["questions"][0]["title"] == "年龄"
    attempt = ok(
        client.put(
            f"/api/attempts/{attempt['_id']}",
            json={"revision": attempt["revision"], "answers": {iid: "25"}},
        )
    )
    ok(
        client.post(
            f"/api/attempts/{attempt['_id']}/submit",
            json={"revision": attempt["revision"]},
        )
    )
    r = database.responses.find_one({"survey_id": s["_id"]})
    assert r["version"] == 1 and "source" not in r
    assert set(r["answers"][0]) == {"question_id", "value"}


def test_library_multiple_versions_unique_revision_and_revoked_member(client, other):
    a = new(client)
    b = newer(client, a)
    grant(client, other, a["version"])
    g = grant(client, other, b["version"])
    lib = ok(other.post("/api/libraries", json={"name": "题库"}), 201)
    lid = lib["_id"]
    for i, v in enumerate([a["version"], b["version"]]):
        ok(
            other.post(
                f"/api/libraries/{lid}/items",
                json={
                    "revision": i + 1,
                    "question_version_id": v["_id"],
                    "position": i,
                },
            ),
            201,
        )
    assert (
        other.post(
            f"/api/libraries/{lid}/items",
            json={"revision": 3, "question_version_id": a["version"]["_id"]},
        ).status_code
        == 409
    )
    assert (
        other.post(
            f"/api/libraries/{lid}/items",
            json={"revision": 1, "question_version_id": a["version"]["_id"]},
        ).status_code
        == 409
    )
    data = ok(other.get(f"/api/libraries/{lid}/items"))
    assert data["total"] == 2 and data["library"]["revision"] == 3
    item = next(
        i for i in data["items"] if i["question_version_id"] == a["version"]["_id"]
    )
    assert (
        other.put(
            f"/api/libraries/{lid}/items/{item['_id']}",
            json={"revision": 3, "question_version_id": b["version"]["_id"]},
        ).status_code
        == 409
    )
    ok(client.post(f"/api/grants/{g['_id']}/revoke", json={"revision": 1}))
    data = ok(other.get(f"/api/libraries/{lid}/items"))
    assert sum(i["available"] for i in data["items"]) == 1
    ok(
        other.post(
            f"/api/libraries/{lid}/items/{item['_id']}/remove", json={"revision": 3}
        )
    )
    assert client.get(f"/api/libraries/{lid}/items").status_code == 404


def test_statistics_duplicate_instances_and_version_isolation(client):
    a = new(client)
    s = survey(client)
    for _ in range(2):
        s = imp(client, s, a["version"])
    s = publish(client, allow_repeat(client, s))
    ids = [q["id"] for q in s["draft"]["questions"]]
    submit(client, s, {ids[0]: "20", ids[1]: "40"})
    t = publish(client, allow_repeat(client, imp(client, survey(client), a["version"])))
    submit(client, t, {t["draft"]["questions"][0]["id"]: "60"})
    result = ok(client.get(f"/api/question-versions/{a['version']['_id']}/statistics"))
    assert (
        result["coverage_surveys"],
        result["valid_responses"],
        result["valid_answers"],
    ) == (2, 2, 3)
    assert result["average"] == 40 and result["min"] == 20 and result["max"] == 60
    assert sum(x["count"] for x in result["distribution"]) == 3
    b = newer(client, a)
    assert (
        ok(client.get(f"/api/question-versions/{b['version']['_id']}/statistics"))[
            "valid_answers"
        ]
        == 0
    )
    assert (
        client.get(
            f"/api/question-versions/{a['version']['_id']}/statistics?boundaries=3&boundaries=2"
        ).status_code
        == 422
    )


def test_multiselect_denominator_is_answer_occurrences(client):
    a = new(client, "multiple_choice")
    s = publish(client, allow_repeat(client, imp(client, survey(client), a["version"])))
    iid = s["draft"]["questions"][0]["id"]
    submit(client, s, {iid: ["a", "b"]})
    submit(client, s, {iid: ["b", "c"]})
    r = ok(client.get(f"/api/question-versions/{a['version']['_id']}/statistics"))
    assert r["valid_answers"] == 2 and [x["count"] for x in r["options"]] == [1, 2, 1]
    assert sum(x["ratio"] for x in r["options"]) == 2


def test_statistics_use_grant_is_not_data_grant_and_revoke_excludes(client, other):
    a = new(client)
    grant(client, other, a["version"])
    s = publish(other, allow_repeat(other, imp(other, survey(other), a["version"])))
    submit(other, s, {s["draft"]["questions"][0]["id"]: "33"})
    vid = a["version"]["_id"]
    assert (
        ok(client.get(f"/api/question-versions/{vid}/statistics"))["valid_answers"] == 0
    )
    assert (
        client.post(
            "/api/grants",
            json={
                "kind": "aggregate",
                "question_version_id": vid,
                "username": other.account["username"],
                "survey_id": s["_id"],
            },
        ).status_code
        == 404
    )
    owner = ok(client.get("/api/auth/me"))
    client.account = owner
    g = grant(other, client, a["version"], "aggregate", s["_id"])
    assert ok(client.get(f"/api/question-versions/{vid}/statistics"))["average"] == 33
    ok(other.post(f"/api/grants/{g['_id']}/revoke", json={"revision": 1}))
    assert (
        ok(client.get(f"/api/question-versions/{vid}/statistics"))["valid_answers"] == 0
    )
    assert (
        client.get(
            f"/api/question-versions/{vid}/statistics?survey_id=" + s["_id"]
        ).status_code
        == 403
    )


def test_usage_distinct_surveys_and_private_title_hidden(client, other):
    a = new(client)
    grant(client, other, a["version"])
    s = imp(other, survey(other), a["version"])
    s["draft"]["title"] = "绝密问卷标题"
    s = ok(save(other, s))
    s = publish(other, s)
    publish(other, s)
    r = ok(client.get(f"/api/questions/{a['question']['_id']}/usage"))
    assert (
        r["used_surveys"]
        == r["current_published_surveys"]
        == r["historical_published_surveys"]
        == 1
    )
    assert not r["items"] and "绝密" not in json.dumps(r, ensure_ascii=False)
    own = ok(other.get(f"/api/questions/{a['question']['_id']}/usage"))
    assert own["items"][0]["published_versions"] == [2, 1]


def test_old_local_save_reusable_does_not_link_historical_answers(
    client, published, database
):
    before = database.survey_versions.find_one({"survey_id": published["_id"]})
    r = ok(
        client.post(
            f"/api/surveys/{published['_id']}/questions/save-reusable",
            json={"revision": published["revision"], "instance_id": "q3"},
        ),
        201,
    )
    assert (
        r["survey"]["draft"]["questions"][2]["source"]["question_id"]
        == r["question"]["_id"]
    )
    assert database.survey_versions.find_one({"_id": before["_id"]}) == before
    assert (
        ok(client.get(f"/api/question-versions/{r['version']['_id']}/statistics"))[
            "coverage_surveys"
        ]
        == 0
    )


def test_phase1_schema_upgrade_preserves_business_documents(
    client, published, database, tmp_path
):
    from conftest import start
    token=start(client,published,True)
    ok(client.post('/api/responses',json={'token':token,'answers':{'q1':'worker','q3':20}}))
    schemas = json.loads(
        (ROOT / "database/legacy/collection_validators.phase1-1.1.0.json").read_text(
            "utf8"
        )
    )
    legacy = database.client["survey_lab_test_phase1_" + uuid4().hex]
    try:
        for n, schema in schemas.items():
            legacy.create_collection(n, validator={"$jsonSchema": schema})
            # Session-scoped test DB also contains earlier phase-two cases. Copy only
            # this source-free phase-one fixture, never mixed newer business data.
            query = ({'_id':published['owner_id']} if n=='users' else
                     {'user_id':published['owner_id']} if n=='sessions' else
                     {'_id':published['_id']} if n=='surveys' else {'survey_id':published['_id']})
            docs = list(database[n].find(query))
            if docs:
                legacy[n].insert_many(docs)
        before = {n: list(legacy[n].find({})) for n in schemas}
        journal = tmp_path / "phase2.json"
        upgrade(legacy, journal)
        initialize(legacy)
        assert all(list(legacy[n].find({})) == docs for n, docs in before.items())
        assert len(legacy.list_collection_names()) == 11
        with TestClient(
            create_app(legacy, "phase2-test-secret-at-least-32-characters")
        ) as c:
            c.cookies.update(client.cookies)
            assert c.get(f"/api/surveys/{published['_id']}").status_code == 200
        rollback(legacy, journal)
        assert all(list(legacy[n].find({})) == docs for n, docs in before.items())
    finally:
        database.client.drop_database(legacy.name)


def test_downgrade_after_new_business_data_is_rejected(client, database, tmp_path):
    from app.errors import BusinessError
    schemas=json.loads((ROOT/'database/legacy/collection_validators.phase1-1.1.0.json').read_text('utf8'))
    db=database.client['survey_lab_test_downgrade_'+uuid4().hex]
    try:
        for name,schema in schemas.items():db.create_collection(name,validator={'$jsonSchema':schema})
        journal=tmp_path/'downgrade.json';upgrade(db,journal);initialize(db)
        db.questions.insert_one({'_id':'q','owner_id':'owner','title':'age','latest_version_id':'v','version_seq':1,'revision':1,'archived':False,'activity_seq':0,'created_at':__import__('app.security',fromlist=['now']).now(),'updated_at':__import__('app.security',fromlist=['now']).now(),'schema_version':1})
        with pytest.raises(BusinessError,match='第二阶段业务数据'):rollback(db,journal)
    finally:database.client.drop_database(db.name)


@pytest.mark.parametrize(
    "collection,document",
    [
        ("questions", {"_id": "bad"}),
        ("question_versions", {"_id": "bad"}),
        ("resource_grants", {"kind": "admin"}),
        ("question_library_items", {"question_version_id": 7}),
        ("question_libraries", {"name": None}),
    ],
)
def test_phase2_schema_rejects_bad_direct_writes(
    client, database, collection, document
):
    with pytest.raises(WriteError):
        database[collection].insert_one(document)
