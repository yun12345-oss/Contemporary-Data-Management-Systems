from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from app.security import now
from conftest import start, publish_survey


def submit(client, token, answers=None):
    return client.post(
        "/api/responses",
        json={
            "token": token,
            "answers": answers or {"q1": "worker", "q3": 20, "q4": "很好"},
        },
    )


def test_full_flow_idempotency_and_anonymity(client, published, database):
    token = start(client, published, True)
    r = submit(client, token)
    assert r.status_code == 200, r.text
    repeated = submit(client, token)
    assert repeated.json() == r.json()
    rows = list(database.responses.find({"survey_id": published["_id"]}))
    assert len(rows) == 1 and "user_id" not in rows[0] and rows[0]["anonymous"]
    stats = client.get(f"/api/surveys/{published['_id']}/statistics").json()
    assert stats["total"] == 1
    assert stats["questions"][0]["options"][1]["count"] == 1
    assert stats["questions"][1]["answered"] == 0
    assert stats["questions"][2]["average"] == 20
    values = client.get(f"/api/surveys/{published['_id']}/questions/q4/values").json()
    assert values["items"][0]["value"] == "很好"
    assert not {"user_id", "respondent_key", "attempt_id"} & set(values["items"][0])


def test_permission_isolation(client, published, app):
    with TestClient(app) as other:
        other.post(
            "/api/auth/register",
            json={"username": "other_" + uuid4().hex[:10], "password": "OtherPass123"},
        )
        sid = published["_id"]
        for path in [
            f"/surveys/{sid}",
            f"/surveys/{sid}/statistics",
            f"/surveys/{sid}/versions",
            f"/surveys/{sid}/questions/q4/values",
        ]:
            assert other.get("/api" + path).status_code == 404
        assert other.get("/api/surveys").json()["total"] == 0
        assert (
            other.patch(
                f"/api/surveys/{sid}/status", json={"status": "closed"}
            ).status_code
            == 404
        )


def test_token_other_user(client, published, app):
    token = start(client, published)
    with TestClient(app) as other:
        other.post(
            "/api/auth/register",
            json={"username": "other_" + uuid4().hex[:10], "password": "OtherPass123"},
        )
        assert submit(other, token).status_code == 403
        assert (
            other.post(
                "/api/evaluate", json={"token": token, "answers": {}}
            ).status_code
            == 403
        )


def test_invalid_answer_no_write(client, published, database):
    token = start(client, published)
    r = submit(client, token, {"q1": "worker", "q3": 121})
    assert r.status_code == 422 and "q3" in r.json()["details"]
    assert database.responses.count_documents({"survey_id": published["_id"]}) == 0


def test_close_and_deadline(client, published, database):
    token = start(client, published)
    database.surveys.update_one(
        {"_id": published["_id"]}, {"$set": {"deadline": now() - timedelta(seconds=1)}}
    )
    assert submit(client, token).status_code == 409
    database.surveys.update_one({"_id": published["_id"]}, {"$set": {"deadline": None}})
    assert (
        client.patch(
            f"/api/surveys/{published['_id']}/status", json={"status": "closed"}
        ).status_code
        == 200
    )
    assert submit(client, token).status_code == 409


def test_concurrent_repeat_forbidden(client, published, database):
    tokens = [start(client, published), start(client, published)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda t: submit(client, t).status_code, tokens))
    assert sorted(codes) == [200, 409]
    assert database.responses.count_documents({"survey_id": published["_id"]}) == 1


def test_concurrent_same_attempt(client, published, database):
    token = start(client, published)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: submit(client, token), range(3)))
    assert all(r.status_code == 200 for r in results)
    assert len({r.json()["id"] for r in results}) == 1


def test_repeat_allowed(client, definition, database):
    definition["allow_repeat"] = True
    s = publish_survey(client, definition)
    for _ in range(2):
        assert submit(client, start(client, s)).status_code == 200
    assert database.responses.count_documents({"survey_id": s["_id"]}) == 2


def test_old_version_after_publish(client, published, database):
    token = start(client, published)
    draft = deepcopy(published["draft"])
    draft["questions"][2]["title"] = "年龄（新版本）"
    saved = client.put(
        f"/api/surveys/{published['_id']}/draft",
        json={"revision": published["revision"], "draft": draft},
    ).json()
    assert (
        client.post(
            f"/api/surveys/{published['_id']}/publish",
            json={"revision": saved["revision"]},
        ).status_code
        == 200
    )
    assert submit(client, token).status_code == 200
    old = client.get(f"/api/surveys/{published['_id']}/statistics?version=1").json()
    new = client.get(f"/api/surveys/{published['_id']}/statistics?version=2").json()
    assert old["questions"][2]["title"] == "年龄" and old["total"] == 1
    assert new["questions"][2]["title"] == "年龄（新版本）" and new["total"] == 0


def test_optimistic_edit_and_invalid_publish(client, published):
    path = f"/api/surveys/{published['_id']}/draft"
    data = {"revision": published["revision"], "draft": published["draft"]}
    assert client.put(path, json=data).status_code == 200
    assert client.put(path, json=data).status_code == 409
    current = client.get(f"/api/surveys/{published['_id']}").json()
    bad = deepcopy(current["draft"])
    bad["questions"][0]["routing"]["default_target"] = "q1"
    saved = client.put(
        path, json={"revision": current["revision"], "draft": bad}
    ).json()
    assert (
        client.post(
            f"/api/surveys/{published['_id']}/publish",
            json={"revision": saved["revision"]},
        ).status_code
        == 422
    )
    assert len(client.get(f"/api/surveys/{published['_id']}/versions").json()) == 1


def test_multiple_and_average(client, definition, app):
    definition["allow_repeat"] = True
    s = publish_survey(client, definition)
    assert (
        submit(
            client, start(client, s), {"q1": "student", "q2": ["a", "b"], "q3": 0}
        ).status_code
        == 200
    )
    assert (
        submit(
            client, start(client, s), {"q1": "student", "q2": ["b", "c"], "q3": 20}
        ).status_code
        == 200
    )
    stats = client.get(f"/api/surveys/{s['_id']}/statistics").json()
    assert [o["count"] for o in stats["questions"][1]["options"]] == [1, 2, 1]
    assert stats["questions"][2]["average"] == 10


def test_no_login_and_csrf(app):
    with TestClient(app) as c:
        assert c.get("/api/surveys").status_code == 401
        assert (
            c.post(
                "/api/auth/register",
                headers={"Origin": "https://evil.example"},
                json={"username": "anyone", "password": "password123"},
            ).status_code
            == 403
        )


def test_auth_casefold_logout(app):
    with TestClient(app) as c:
        name = "Auth_" + uuid4().hex[:8]
        body = {"username": name, "password": "StrongPass123"}
        assert c.post("/api/auth/register", json=body).status_code == 201
        assert (
            "HttpOnly"
            in c.cookies.jar._cookies["testserver.local"]["/"]["survey_session"]._rest
        )
        assert (
            c.post(
                "/api/auth/register", json={**body, "username": name.lower()}
            ).status_code
            == 409
        )
        assert c.post("/api/auth/logout").status_code == 200
        assert c.get("/api/auth/me").status_code == 401
        assert (
            c.post(
                "/api/auth/login", json={**body, "password": "WrongPass123"}
            ).status_code
            == 401
        )
        assert (
            c.post(
                "/api/auth/login", json={**body, "username": name.lower()}
            ).status_code
            == 200
        )


def test_token_tamper(client, published):
    token = start(client, published)
    assert submit(client, token + "x").status_code == 401


def test_time_and_pagination(client, published):
    assert submit(client, start(client, published)).status_code == 200
    root = f"/api/surveys/{published['_id']}"
    assert (
        client.get(root + "/statistics?start=2100-01-01T00:00:00Z").json()["total"] == 0
    )
    assert (
        client.get(
            root + "/statistics?start=2100-01-01T00:00:00Z&end=2000-01-01T00:00:00Z"
        ).status_code
        == 422
    )
    assert client.get(root + "/questions/q4/values?page=2").json()["items"] == []


def test_database_validation(client, database):
    from pymongo.errors import WriteError
    import pytest

    with pytest.raises(WriteError):
        database.responses.insert_one({"invalid": "record"})
