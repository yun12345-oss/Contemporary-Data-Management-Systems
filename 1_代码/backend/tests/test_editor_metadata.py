def test_publish_returns_committed_metadata_without_embedding_it_in_version(
    client, published, database
):
    sid = published["_id"]
    r = client.post(
        f"/api/surveys/{sid}/publish",
        json={
            "revision": published["revision"],
            "deadline": "2030-01-01T12:30:45.123Z",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == 2
    assert data["survey"]["revision"] == published["revision"] + 1
    assert (
        data["survey"]["current_version"] == 2
        and data["survey"]["status"] == "published"
    )
    assert data["survey"]["deadline"] == "2030-01-01T12:30:45.123000+00:00"
    assert "draft" not in data["survey"]
    assert "survey" not in database.survey_versions.find_one({"_id": data["_id"]})


def test_close_revision_conflict_preserves_state_and_returns_metadata(
    client, published, database
):
    sid = published["_id"]
    old = published["revision"]
    saved = client.put(
        f"/api/surveys/{sid}/draft", json={"revision": old, "draft": published["draft"]}
    ).json()
    conflict = client.patch(
        f"/api/surveys/{sid}/status", json={"status": "closed", "revision": old}
    )
    assert conflict.status_code == 409
    assert database.surveys.find_one({"_id": sid})["status"] == "published"
    closed = client.patch(
        f"/api/surveys/{sid}/status",
        json={"status": "closed", "revision": saved["revision"]},
    )
    assert closed.status_code == 200
    body = closed.json()
    assert body["ok"] and body["survey"]["status"] == "closed"
    assert body["survey"]["revision"] == saved["revision"] + 1
    assert "draft" not in body["survey"]
