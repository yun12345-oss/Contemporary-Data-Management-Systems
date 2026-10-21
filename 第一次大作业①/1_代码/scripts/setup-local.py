"""初始化本地密钥、副本集，等待主节点就绪。不会清空数据库。"""

import secrets
import time
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import OperationFailure

root = Path(__file__).resolve().parents[1]
env = root / ".env"
if not env.exists():
    env.write_text(
        "MONGO_URI=mongodb://127.0.0.1:27019/?replicaSet=survey-rs\nMONGO_DB=survey_lab\nSECRET_KEY="
        + secrets.token_urlsafe(48)
        + "\nCOOKIE_SECURE=false\n",
        encoding="utf-8",
    )
client = MongoClient(
    "mongodb://127.0.0.1:27019/?directConnection=true", serverSelectionTimeoutMS=5000
)
try:
    client.admin.command(
        "replSetInitiate",
        {"_id": "survey-rs", "members": [{"_id": 0, "host": "127.0.0.1:27019"}]},
    )
except OperationFailure as exc:
    if exc.code != 23:
        raise
for _ in range(60):
    if client.admin.command("hello").get("isWritablePrimary"):
        break
    time.sleep(0.5)
else:
    raise RuntimeError("MongoDB primary election timed out")
print("Local MongoDB replica set is ready.")
