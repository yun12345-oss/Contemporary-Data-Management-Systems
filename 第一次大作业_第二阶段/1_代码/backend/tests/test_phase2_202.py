"""2.0.2 real MongoDB regressions; temporary fixture database only."""
from copy import deepcopy
import pytest
from test_phase2 import new, newer, grant, ok, other, survey, imp, publish, submit, allow_repeat

@pytest.mark.parametrize("revoke_target", [False, True])
def test_library_old_revoked_target_authorization_controls_update(client, other, revoke_target):
    old = new(client)
    latest = newer(client, old)
    g1 = grant(client, other, old["version"])
    g2 = grant(client, other, latest["version"])
    library = ok(other.post("/api/libraries", json={"name": "202 update"}), 201)
    lid = library["_id"]
    ok(other.post(f"/api/libraries/{lid}/items", json={"revision": 1, "question_version_id": old["version"]["_id"]}), 201)
    ok(client.post(f"/api/grants/{g1['_id']}/revoke", json={"revision": 1}))
    before = ok(other.get(f"/api/libraries/{lid}/items"))
    item = before["items"][0]
    assert item["available"] is False and item["version"] is None
    assert item["question_id"] == old["question"]["_id"]
    if revoke_target:
        ok(client.post(f"/api/grants/{g2['_id']}/revoke", json={"revision": 1}))
    response = other.put(f"/api/libraries/{lid}/items/{item['_id']}", json={"revision": before["library"]["revision"], "question_version_id": latest["version"]["_id"]})
    after = ok(other.get(f"/api/libraries/{lid}/items"))
    if revoke_target:
        assert response.status_code == 403
        assert after["items"][0]["question_version_id"] == old["version"]["_id"]
        assert after["library"]["revision"] == before["library"]["revision"]
    else:
        ok(response)
        assert after["items"][0]["question_version_id"] == latest["version"]["_id"]
        assert after["items"][0]["available"] is True

def test_statistics_zero_answer_coverage_and_submission_time(client):
    q = new(client)
    s = publish(client, allow_repeat(client, imp(client, survey(client), q["version"])))
    path = f"/api/question-versions/{q['version']['_id']}/statistics"
    empty = ok(client.get(path, params={"start": "2099-01-01T00:00:00Z"}))
    assert empty["coverage_surveys"] == 1 and empty["valid_answers"] == 0
    submit(client, s, {s["draft"]["questions"][0]["id"]: "25"})
    assert ok(client.get(path))["valid_answers"] == 1
    excluded = ok(client.get(path, params={"start": "2099-01-01T00:00:00Z"}))
    assert excluded["coverage_surveys"] == 1 and excluded["answered_surveys"] == 0
    usage = ok(client.get(f"/api/questions/{q['question']['_id']}/usage"))
    assert usage["current_published_surveys"] == 1
    assert usage["historical_published_surveys"] == 1
    assert usage["used_surveys"] == 1
