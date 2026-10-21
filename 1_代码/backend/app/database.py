import json
from pymongo import MongoClient
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from app.config import ROOT, settings
from app.errors import require


def connect():
    return MongoClient(settings.mongo_uri, tz_aware=True, serverSelectionTimeoutMS=5000)


def validator_definitions():
    return json.loads((ROOT / "database/collection_validators.json").read_text("utf-8"))


def initialize(db):
    """仅初始化新集合；已有约束不符时停止，不能在启动时隐式迁移。"""
    validators = validator_definitions()
    existing = {c["name"]: c.get("options", {}) for c in db.list_collections()}
    for name, schema in validators.items():
        if name in existing:
            options = existing[name]
            require(
                options.get("validator") == {"$jsonSchema": schema}
                and options.get("validationLevel", "strict") == "strict"
                and options.get("validationAction", "error") == "error",
                "数据库约束与当前程序不一致。请停止写入，先运行 backend/scripts/upgrade_database.py --check，再显式升级；启动不会修改已有约束。",
                500,
            )
    for name, schema in validators.items():
        spec = {"$jsonSchema": schema}
        if name not in existing:
            db.create_collection(name, validator=spec)
    definitions = json.loads((ROOT / "database/indexes.json").read_text("utf-8"))
    for name, indexes in definitions.items():
        for index in indexes:
            options = {k: v for k, v in index.items() if k != "keys"}
            db[name].create_index([tuple(x) for x in index["keys"]], **options)


def transact(db, callback):
    # 副本集事务同时保护问卷状态检查、去重检查与答案写入。
    with db.client.start_session() as session:
        return session.with_transaction(
            callback,
            read_concern=ReadConcern("snapshot"),
            write_concern=WriteConcern("majority"),
        )
