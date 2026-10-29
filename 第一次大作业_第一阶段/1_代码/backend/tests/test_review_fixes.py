from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pymongo.errors import WriteError
from app.domain.questions import handler, validate_answer
from app.domain.rules import check_definition
from app.errors import BusinessError
from app.security import now
from conftest import publish_survey, start


@pytest.mark.parametrize("kind", ["multiple", "integer", "text"])
def test_unanswerable_required_questions_rejected(client, definition, database, kind):
    if kind == "multiple":
        definition["questions"][1]["validation"] = {"max_choices": 0}
    elif kind == "integer":
        definition["questions"][2]["validation"] = {
            "min": 0.1,
            "max": 0.9,
            "integer_only": True,
        }
    else:
        definition["questions"][3]["required"] = True
        definition["questions"][3]["validation"] = {"max_length": 0}
    survey = client.post("/api/surveys", json={"title": "不可回答配置"}).json()
    saved = client.put(
        f"/api/surveys/{survey['_id']}/draft", json={"revision": 1, "draft": definition}
    )
    assert saved.status_code == 200
    result = client.post(
        f"/api/surveys/{survey['_id']}/publish",
        json={"revision": saved.json()["revision"]},
    )
    assert result.status_code == 422
    assert database.survey_versions.count_documents({"survey_id": survey["_id"]}) == 0
    current = database.surveys.find_one({"_id": survey["_id"]})
    assert current["status"] == "draft" and current["current_version"] == 0


@pytest.mark.parametrize("low,high", [(0.1, 1), (-0.9, 0), (1, 1)])
def test_integer_interval_with_valid_point(definition, low, high):
    definition["questions"][2]["validation"] = {
        "min": low,
        "max": high,
        "integer_only": True,
    }
    check_definition(definition)


@pytest.mark.parametrize(
    "value", [10**400, -(10**400), float("inf"), float("-inf"), float("nan")]
)
def test_extreme_domain_numbers_never_overflow(definition, value):
    with pytest.raises(BusinessError):
        validate_answer(definition["questions"][2], value)
    definition["questions"][2]["validation"]["max"] = value
    with pytest.raises(BusinessError):
        check_definition(definition)


def test_extreme_config_rejected_before_bson(client, definition, database):
    survey = client.post("/api/surveys", json={"title": "极端数字"}).json()
    definition["questions"][2]["validation"]["max"] = 10**20
    response = client.put(
        f"/api/surveys/{survey['_id']}/draft", json={"revision": 1, "draft": definition}
    )
    assert response.status_code == 422
    current = database.surveys.find_one({"_id": survey["_id"]})
    assert current["revision"] == 1 and not current["draft"]["questions"]


def test_extreme_submission_rejected_without_write(client, published, database):
    token = start(client, published)
    r = client.post(
        "/api/responses",
        json={"token": token, "answers": {"q1": "worker", "q3": 10**400}},
    )
    assert r.status_code == 422
    assert database.responses.count_documents({"survey_id": published["_id"]}) == 0


def test_nested_extreme_condition_rejected(client, definition):
    survey = client.post("/api/surveys", json={"title": "条件数字"}).json()
    definition["questions"][2]["routing"]["rules"] = [
        {
            "condition": {
                "all": [{"question_id": "q3", "operator": "gt", "value": 10**400}]
            },
            "target": "END",
        }
    ]
    assert (
        client.put(
            f"/api/surveys/{survey['_id']}/draft",
            json={"revision": 1, "draft": definition},
        ).status_code
        == 422
    )


def test_counts_people_anonymous_and_repeat(client, definition, app, database):
    definition["allow_repeat"] = True
    survey = publish_survey(client, definition)
    sid = survey["_id"]

    def answer(c, data, anonymous):
        return c.post(
            "/api/responses",
            json={"token": start(c, survey, anonymous), "answers": data},
        )

    assert (
        answer(client, {"q1": "student", "q2": ["a", "b"], "q3": 20}, True).status_code
        == 200
    )
    assert (
        answer(client, {"q1": "student", "q2": ["b", "c"], "q3": 30}, False).status_code
        == 200
    )
    assert answer(client, {"q1": "worker", "q3": 40}, True).status_code == 200
    split = now()
    with TestClient(app) as other:
        assert (
            other.post(
                "/api/auth/register",
                json={
                    "username": "counts_" + uuid4().hex[:12],
                    "password": "StrongPass123",
                },
            ).status_code
            == 201
        )
        assert (
            answer(
                other, {"q1": "student", "q2": ["a", "c"], "q3": 50, "q4": "建议"}, True
            ).status_code
            == 200
        )
    stats = client.get(f"/api/surveys/{sid}/statistics").json()
    assert stats["total"] == 4 and stats["respondent_count"] == 2
    single, multiple, number, text = stats["questions"]
    assert single["answered"] == 4 and single["respondent_count"] == 2
    assert [(o["count"], o["respondent_count"]) for o in single["options"]] == [
        (3, 2),
        (1, 1),
    ]
    assert multiple["answered"] == 3 and multiple["respondent_count"] == 2
    assert [(o["count"], o["respondent_count"]) for o in multiple["options"]] == [
        (2, 2),
        (2, 1),
        (2, 2),
    ]
    assert text["answered"] == 1 and text["respondent_count"] == 1
    assert number["average"] == 35
    assert "respondent_key" not in str(stats)
    # 同一筛选内去重；不存在的未来时间窗口返回零。
    empty = client.get(
        f"/api/surveys/{sid}/statistics?start=2100-01-01T00:00:00Z"
    ).json()
    assert empty["total"] == 0 and empty["respondent_count"] == 0
    assert all(q["respondent_count"] == 0 for q in empty["questions"])
    # 仅将测试构造的最后一条时间推进一天，验证筛选不沿用全局人数。
    database.responses.update_one(
        {
            "survey_id": sid,
            "answers": {"$elemMatch": {"question_id": "q3", "value": 50}},
        },
        {"$set": {"submitted_at": split + timedelta(days=1)}},
    )
    filtered = client.get(
        f"/api/surveys/{sid}/statistics",
        params={"start": (split + timedelta(hours=1)).isoformat()},
    ).json()
    assert filtered["total"] == filtered["respondent_count"] == 1
    draft = client.get(f"/api/surveys/{sid}").json()
    assert (
        client.post(
            f"/api/surveys/{sid}/publish", json={"revision": draft["revision"]}
        ).status_code
        == 200
    )
    new = client.get(f"/api/surveys/{sid}/statistics?version=2").json()
    assert new["total"] == new["respondent_count"] == 0
    assert (
        client.get(f"/api/surveys/{sid}/statistics?version=1").json()[
            "respondent_count"
        ]
        == 2
    )


@pytest.mark.parametrize(
    "collection,field,value",
    [
        ("responses", "answers", [{"value": 20}]),
        ("responses", "answers", [{"question_id": "q3", "value": True}]),
        ("responses", "answers", [{"question_id": "q3", "value": {"bad": 1}}]),
        ("responses", "version_id", 42),
        ("responses", "respondent_key", False),
        ("survey_versions", "definition", {}),
        ("surveys", "draft", {}),
        ("surveys", "share_code", 42),
    ],
)
def test_deep_database_constraints(
    client, published, database, collection, field, value
):
    if collection == "responses":
        assert (
            client.post(
                "/api/responses",
                json={
                    "token": start(client, published),
                    "answers": {"q1": "worker", "q3": 20},
                },
            ).status_code
            == 200
        )
        doc = database.responses.find_one({"survey_id": published["_id"]})
    elif collection == "survey_versions":
        doc = database.survey_versions.find_one({"survey_id": published["_id"]})
    else:
        doc = database.surveys.find_one({"_id": published["_id"]})
    doc[field] = value
    with pytest.raises(WriteError):
        database[collection].replace_one({"_id": doc["_id"]}, doc)
