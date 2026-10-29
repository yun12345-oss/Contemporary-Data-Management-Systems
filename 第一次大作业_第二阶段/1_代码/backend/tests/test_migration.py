import json
from uuid import uuid4
from pathlib import Path
import pytest
from app.config import ROOT
from app.database import initialize, validator_definitions
from app.errors import BusinessError
from app.migration import inspect_upgrade, upgrade, rollback
import app.migration as migration
from conftest import start


def legacy_copy(database, source):
    name = "survey_lab_test_legacy_" + uuid4().hex
    db = database.client[name]
    old = json.loads(
        (ROOT / "database/legacy/collection_validators.v1.json").read_text("utf-8")
    )
    for collection, schema in old.items():
        db.create_collection(collection, validator={"$jsonSchema": schema})
        docs = list(source[collection].find({}))
        if docs:
            db[collection].insert_many(docs)
    return db


def test_upgrade_old_data_and_explicit_rollback(client, published, database, tmp_path):
    token = start(client, published, True)
    assert (
        client.post(
            "/api/responses",
            json={"token": token, "answers": {"q1": "worker", "q3": 20}},
        ).status_code
        == 200
    )
    db = legacy_copy(database, database)
    try:
        before = {
            n: list(db[n].find({}).sort("_id", 1)) for n in validator_definitions()
        }
        with pytest.raises(BusinessError):
            initialize(db)
        report, _ = inspect_upgrade(db)
        assert all(r["invalid"] == 0 and r["needs_upgrade"] for r in report.values())
        path = tmp_path / "upgrade.json"
        assert upgrade(db, path)["state"] == "complete"
        initialize(db)
        assert all(
            list(db[n].find({}).sort("_id", 1)) == docs for n, docs in before.items()
        )
        assert not any(r["needs_upgrade"] for r in inspect_upgrade(db)[0].values())
        assert rollback(db, path)["state"] == "rolled_back"
        assert all(
            r["needs_upgrade"]
            for n, r in inspect_upgrade(db)[0].items()
            if n in json.loads((ROOT / "database/legacy/collection_validators.v1.json").read_text("utf-8"))
        )
    finally:
        database.client.drop_database(db.name)


def test_failed_upgrade_restores_constraints(client, database, tmp_path, monkeypatch):
    db = legacy_copy(database, database)
    try:
        original = migration.set_options
        counter = [0]

        def fail_once(db, name, options):
            counter[0] += 1
            if counter[0] == 3:
                raise RuntimeError("simulated interruption")
            return original(db, name, options)

        monkeypatch.setattr(migration, "set_options", fail_once)
        path = tmp_path / "failed.json"
        with pytest.raises(RuntimeError):
            upgrade(db, path)
        assert json.loads(path.read_text())["state"] == "rolled_back"
        assert all(
            r["needs_upgrade"]
            for n, r in inspect_upgrade(db)[0].items()
            if n != "attempts"
        )
    finally:
        database.client.drop_database(db.name)


def test_preflight_invalid_data_leaves_every_validator_unchanged(
    client, database, tmp_path
):
    db = legacy_copy(database, database)
    try:
        # 旧约束允许 share_code 为数字，目标约束不允许。
        from app.security import now

        db.surveys.insert_one(
            {
                "_id": "legacy",
                "owner_id": "user",
                "share_code": 42,
                "status": "draft",
                "draft": {},
                "revision": 1,
                "current_version": 0,
                "schema_version": 1,
            }
        )
        report, _ = inspect_upgrade(db)
        assert report["surveys"]["invalid"] == 1
        with pytest.raises(BusinessError):
            upgrade(db, tmp_path / "blocked.json")
        assert not (tmp_path / "blocked.json").exists()
        assert all(
            r["needs_upgrade"]
            for n, r in inspect_upgrade(db)[0].items()
            if n != "attempts"
        )
    finally:
        database.client.drop_database(db.name)


def test_startup_never_overwrites_unknown_or_future_schema(client, database):
    db = legacy_copy(database, database)
    try:
        future = {
            "$jsonSchema": {
                "bsonType": "object",
                "properties": {"schema_version": {"enum": [1, 2]}},
            }
        }
        db.command("collMod", "surveys", validator=future)
        with pytest.raises(BusinessError):
            initialize(db)
        with pytest.raises(BusinessError):
            inspect_upgrade(db)
        assert db.surveys.options()["validator"] == future
    finally:
        database.client.drop_database(db.name)
