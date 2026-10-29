"""显式升级集合约束。维护窗口运行，先全量预检，再记录可恢复日志。"""

import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from bson import json_util
from app.config import ROOT
from app.database import validator_definitions
from app.errors import require


def canonical(value):
    return json_util.dumps(value, sort_keys=True)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write_journal(path, journal):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(canonical(journal), encoding="utf-8")
    temp.replace(path)


def inspect_upgrade(db):
    target = validator_definitions()
    legacy = json.loads(
        (ROOT / "database/legacy/collection_validators.v1.json").read_text("utf-8")
    )
    options = {c["name"]: c.get("options", {}) for c in db.list_collections()}
    require(
        set(legacy) <= set(options),
        "已有库缺少集合，请先检查数据库，不自动推断迁移路径",
        409,
    )
    report = {}
    for name, schema in target.items():
        # 新增集合由普通初始化创建；此流程只升级已有集合。
        if name not in options:
            continue
        current = options[name].get("validator", {})
        require(
            current
            in ({"$jsonSchema": legacy.get(name, schema)}, {"$jsonSchema": schema}),
            f"{name} 的校验器不是已知旧版或目标版，停止升级",
            409,
        )
        invalid = db[name].count_documents({"$nor": [{"$jsonSchema": schema}]})
        report[name] = {
            "count": db[name].count_documents({}),
            "invalid": invalid,
            "needs_upgrade": current != {"$jsonSchema": schema},
        }
    return report, options


def set_options(db, name, options):
    db.command(
        "collMod",
        name,
        validator=options.get("validator", {}),
        validationLevel=options.get("validationLevel", "strict"),
        validationAction=options.get("validationAction", "error"),
    )


def rollback(db, path):
    journal = json_util.loads(Path(path).read_text("utf-8"))
    require(journal["database"] == db.name, "恢复日志不属于此数据库", 409)
    targets = journal["target"]
    options = {c["name"]: c.get("options", {}) for c in db.list_collections()}
    for name, before in journal["before"].items():
        require(
            options.get(name, {}).get("validator", {})
            in (before.get("validator", {}), {"$jsonSchema": targets[name]}),
            "数据库约束已被其他操作改变，拒绝覆盖",
            409,
        )
    for name, before in journal["before"].items():
        set_options(db, name, before)
    journal["state"] = "rolled_back"
    write_journal(path, journal)
    return journal


def upgrade(db, path):
    path = Path(path)
    require(not path.exists(), "升级日志已存在，不能覆盖；请使用新路径", 409)
    report, options = inspect_upgrade(db)
    require(
        not any(r["invalid"] for r in report.values()),
        "旧数据不符合新约束，升级未执行。请先查看 --check 结果并制定修复方案。",
        409,
    )
    target = {n: s for n, s in validator_definitions().items() if n in options}
    journal = {
        "database": db.name,
        "started_at": datetime.now(timezone.utc),
        "state": "prepared",
        "before": {n: options[n] for n in target},
        "target": target,
        "target_hash": fingerprint(target),
        "report": report,
        "applied": [],
    }
    write_journal(path, journal)
    try:
        for name, schema in target.items():
            set_options(db, name, {"validator": {"$jsonSchema": schema}})
            journal["applied"].append(name)
            journal["state"] = "applying"
            write_journal(path, journal)
        journal["state"] = "complete"
        write_journal(path, journal)
        return journal
    except Exception:
        # 普通失败自动恢复；进程中断时可以用相同日志显式 --rollback。
        rollback(db, path)
        raise
