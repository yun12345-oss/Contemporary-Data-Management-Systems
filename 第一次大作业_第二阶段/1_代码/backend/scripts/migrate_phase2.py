"""Maintenance-window schema upgrade; never rewrites business documents."""

import argparse
import json

from app.config import settings
from app.database import connect, initialize
from app.errors import require
from app.migration import inspect_upgrade, rollback, upgrade


def main():
    parser = argparse.ArgumentParser(
        description="停止所有写入后执行；先备份，再预检与升级"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    parser.add_argument("--journal", default="artifacts/phase2/schema-upgrade.json")
    args = parser.parse_args()
    with connect() as client:
        db = client[settings.database]
        if args.check:
            print(json.dumps(inspect_upgrade(db)[0], ensure_ascii=False, indent=2))
        elif args.apply:
            upgrade(db, args.journal)
            initialize(db)
            print("约束升级与新增集合初始化完成；业务文档未改写。")
        else:
            require(
                not db.questions.find_one()
                and not db.surveys.find_one(
                    {"draft.questions.source": {"$type": "object"}}
                )
                and not db.survey_versions.find_one(
                    {"definition.questions.source": {"$type": "object"}}
                ),
                "已有第二阶段业务数据，拒绝降级；需恢复完整维护前备份。",
                409,
            )
            rollback(db, args.journal)
            print("已恢复旧约束；新增空集合保留，不删除数据。")


if __name__ == "__main__":
    main()
