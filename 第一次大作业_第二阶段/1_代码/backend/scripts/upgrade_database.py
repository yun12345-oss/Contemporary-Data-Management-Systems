"""先停止应用写入，再执行 --check；确认后 --apply。日志只保存在本地。"""

import argparse
import json
from datetime import datetime
from app.database import connect
from app.config import ROOT, settings
from app.migration import inspect_upgrade, upgrade, rollback

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", metavar="JOURNAL")
    parser.add_argument("--journal")
    args = parser.parse_args()
    db = connect()[settings.database]
    if args.check:
        print(json.dumps(inspect_upgrade(db)[0], ensure_ascii=False, indent=2))
    elif args.apply:
        path = args.journal or ROOT / ".local" / (
            "constraint-upgrade-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"
        )
        result = upgrade(db, path)
        print("Upgrade " + result["state"] + ". Recovery journal: " + str(path))
    else:
        print("Recovery " + rollback(db, args.rollback)["state"])
