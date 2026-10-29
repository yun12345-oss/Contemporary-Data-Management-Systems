from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from copy import deepcopy
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from app.security import now
from conftest import publish_survey
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError, WriteError


def begin(client, survey, anonymous=False):
    r = client.post(
        f"/api/public/{survey['share_code']}/attempt", json={"anonymous": anonymous}
    )
    assert r.status_code == 200, r.text
    return r.json()


def save(client, attempt, answers, current="q3"):
    return client.put(
        f"/api/attempts/{attempt['_id']}",
        json={
            "revision": attempt["revision"],
            "answers": answers,
            "current_question_id": current,
        },
    )


def finish(client, attempt):
    return client.post(
        f"/api/attempts/{attempt['_id']}/submit", json={"revision": attempt["revision"]}
    )


def other(app, stack):
    c = stack.enter_context(TestClient(app))
    credentials = {
        "username": "resume_" + uuid4().hex[:12],
        "password": "ResumePass123!",
    }
    assert c.post("/api/auth/register", json=credentials).status_code == 201
    return c, credentials


def test_partial_raw_input_resume_across_login_and_device(
    client, published, app, database
):
    with ExitStack() as stack:
        c, credentials = other(app, stack)
        a = begin(c, published, True)
        r = save(c, a, {"q1": "worker", "q3": "-", "q4": "输入尚未完成"}, "q4")
        assert r.status_code == 200, r.text
        saved = r.json()
        assert saved["answers"]["q3"] == "-"
        assert saved["current_question_id"] == "q3" and "q3" in saved["issues"]
        assert "q4" not in saved["path"]
        assert c.post("/api/auth/logout").status_code == 200
        assert c.get(f"/api/attempts/{a['_id']}").status_code == 401
        device = stack.enter_context(TestClient(app))
        assert device.post("/api/auth/login", json=credentials).status_code == 200
        resumed = device.get(f"/api/public/{published['share_code']}/attempt").json()
        assert resumed["answers"] == saved["answers"] and resumed["anonymous"] is True
        assert begin(device, published, False)["anonymous"] is True
        assert finish(device, resumed).status_code == 422
        assert database.responses.count_documents({"attempt_id": a["_id"]}) == 0


def test_revision_conflict_does_not_overwrite(client, published):
    a = begin(client, published)
    first = save(client, a, {"q1": "worker", "q3": "22"}).json()
    assert save(client, a, {"q1": "student"}).status_code == 409
    assert finish(client, a).status_code == 409
    latest = client.get(f"/api/attempts/{a['_id']}").json()
    assert latest["answers"] == first["answers"]


def test_parallel_begin_has_one_active_attempt(client, published, database):
    barrier = Barrier(5)

    def run(_):
        barrier.wait()
        return begin(client, published)

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(run, range(5)))
    assert len({r["_id"] for r in results}) == 1
    assert (
        database.attempts.count_documents(
            {"survey_id": published["_id"], "status": "in_progress"}
        )
        == 1
    )
    doc = database.attempts.find_one({"_id": results[0]["_id"]})
    doc["_id"] = uuid4().hex
    with pytest.raises(DuplicateKeyError):
        database.attempts.insert_one(doc)


def test_skip_cleanup_and_recover_valid_position(client, published):
    a = begin(client, published)
    a = save(client, a, {"q1": "student", "q2": ["a", "b"], "q3": "20"}, "q3").json()
    a = save(client, a, {**a["answers"], "q1": "worker"}, "q2").json()
    assert "q2" not in a["answers"] and a["path"] == ["q1", "q3", "q4"]
    assert a["current_question_id"] in a["path"]
    a = save(client, a, {**a["answers"], "q1": "student"}, "q4").json()
    assert a["current_question_id"] == "q2" and a["path"] == ["q1", "q2"]


@pytest.mark.parametrize("state", ["closed", "expired"])
def test_read_only_restore_but_no_save_submit(client, published, database, state):
    a = begin(client, published)
    a = save(client, a, {"q1": "worker", "q3": "20"}).json()
    fields = (
        {"status": "closed"}
        if state == "closed"
        else {"deadline": now() - timedelta(seconds=1)}
    )
    database.surveys.update_one({"_id": published["_id"]}, {"$set": fields})
    resumed = client.get(f"/api/public/{published['share_code']}/attempt")
    assert resumed.status_code == 200 and resumed.json()["read_only"]
    assert resumed.json()["answers"] == a["answers"]
    assert save(client, a, a["answers"]).status_code == 409
    assert finish(client, a).status_code == 409
    assert begin(client, published)["_id"] == a["_id"]


def test_pinned_version_and_anonymity_atomic_idempotent_submit(
    client, published, database
):
    a = begin(client, published, True)
    a = save(client, a, {"q1": "worker", "q3": "0", "q4": "原始版本"}, "q4").json()
    sid = published["_id"]
    d = deepcopy(published["draft"])
    d["questions"][2]["validation"]["min"] = 100
    s = client.put(
        f"/api/surveys/{sid}/draft",
        json={"revision": published["revision"], "draft": d},
    ).json()
    assert (
        client.post(
            f"/api/surveys/{sid}/publish", json={"revision": s["revision"]}
        ).status_code
        == 200
    )
    assert begin(client, published)["version"] == 1
    barrier = Barrier(3)

    def run(_):
        barrier.wait()
        return finish(client, a)

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run, range(3)))
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    assert len({r.json()["id"] for r in results}) == 1
    assert finish(client, {**a, "revision": 1}).json() == results[0].json()
    stored = database.attempts.find_one({"_id": a["_id"]})
    assert stored["status"] == "submitted" and stored["raw_answers"] == {}
    response = database.responses.find_one({"_id": stored["response_id"]})
    assert response["version"] == 1 and "user_id" not in response
    assert save(client, a, a["answers"]).status_code == 409
    assert (
        client.get(f"/api/attempts/{a['_id']}").json()["receipt"] == results[0].json()
    )


def test_abandon_clears_answers_rejects_late_save_and_allows_new(
    client, published, database
):
    a = begin(client, published)
    a = save(client, a, {"q1": "worker", "q3": "-"}).json()
    r = client.post(
        f"/api/attempts/{a['_id']}/abandon", json={"revision": a["revision"] - 1}
    )
    assert r.status_code == 409
    assert (
        client.post(
            f"/api/attempts/{a['_id']}/abandon", json={"revision": a["revision"]}
        ).status_code
        == 200
    )
    assert database.attempts.find_one({"_id": a["_id"]})["raw_answers"] == {}
    assert save(client, a, {"q1": "student"}).status_code == 409
    assert finish(client, a).status_code == 409
    assert begin(client, published)["_id"] != a["_id"]


def test_drafts_not_in_statistics_and_account_isolation(
    client, published, app, database
):
    a = begin(client, published)
    a = save(client, a, {"q1": "worker", "q3": "20"}).json()
    stats = client.get(f"/api/surveys/{published['_id']}/statistics").json()
    assert stats["total"] == 0 and stats["respondent_count"] == 0
    with ExitStack() as stack:
        c, _ = other(app, stack)
        assert c.get(f"/api/attempts/{a['_id']}").status_code == 404
        assert save(c, a, {}).status_code == 404
        assert finish(c, a).status_code == 404
        assert (
            c.post(
                f"/api/attempts/{a['_id']}/abandon", json={"revision": a["revision"]}
            ).status_code
            == 404
        )
        assert c.get(f"/api/public/{published['share_code']}/attempt").json() is None


@pytest.mark.parametrize(
    "answers",
    [{"unknown": "x"}, {"q1": {"nested": "x"}}, {"q3": True}, {"q4": "x" * 20001}],
)
def test_bad_raw_structure_no_partial_write(client, published, answers):
    a = begin(client, published)
    assert save(client, a, answers).status_code == 422
    assert client.get(f"/api/attempts/{a['_id']}").json()["revision"] == 1


def test_direct_database_schema_rejects_malformed_attempt(client, published, database):
    a = begin(client, published)
    doc = database.attempts.find_one({"_id": a["_id"]})
    doc["_id"] = uuid4().hex
    doc["status"] = "broken"
    with pytest.raises(WriteError):
        database.attempts.insert_one(doc)


def test_submit_transaction_rolls_back_response_on_failure(
    client, published, database, monkeypatch
):
    from pymongo.synchronous.collection import Collection

    a = begin(client, published)
    a = save(client, a, {"q1": "worker", "q3": "20"}).json()
    original = Collection.update_one

    def fail(self, filt, update, *args, **kwargs):
        if (
            self.name == "attempts"
            and update.get("$set", {}).get("status") == "submitted"
        ):
            raise RuntimeError("simulated failure after response insertion")
        return original(self, filt, update, *args, **kwargs)

    monkeypatch.setattr(Collection, "update_one", fail)
    with pytest.raises(RuntimeError):
        finish(client, a)
    assert database.responses.count_documents({"attempt_id": a["_id"]}) == 0
    assert database.attempts.find_one({"_id": a["_id"]})["status"] == "in_progress"


def test_eight_users_parallel_mixed_paths_and_statistics(
    client, definition, app, database
):
    survey = publish_survey(client, definition)
    with ExitStack() as stack:
        clients = [other(app, stack)[0] for _ in range(8)]
        barrier = Barrier(8)

        def run(i):
            c = clients[i]
            a = begin(c, survey, i % 2 == 0)
            raw = {
                "q1": "worker" if i % 2 == 0 else "student",
                "q2": ["a", "b"],
                "q3": str(20 + i),
                "q4": f"用户{i}回答",
            }
            a = save(c, a, raw, "q4").json()
            barrier.wait()
            return finish(c, a)

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(run, range(8)))
        assert all(r.status_code == 200 for r in results), [r.text for r in results]
    rows = list(database.responses.find({"survey_id": survey["_id"]}))
    assert len(rows) == 8 and len({r["respondent_key"] for r in rows}) == 8
    assert all(("q2" in r["path"]) == (not r["anonymous"]) for r in rows)
    stats = client.get(f"/api/surveys/{survey['_id']}/statistics").json()
    assert stats["total"] == stats["respondent_count"] == 8
    assert stats["questions"][1]["answered"] == 4
    assert stats["questions"][2]["average"] == 23.5
    assert sorted(
        a["value"] for r in rows for a in r["answers"] if a["question_id"] == "q4"
    ) == [f"用户{i}回答" for i in range(8)]
