"""可重复导入演示数据；不清空已有用户和问卷。"""

import json
from app.database import connect, initialize
from app.config import settings, ROOT
from app.security import passwords, now, uid, Security
from app.schemas import SaveDraft, Definition, Publish, Submit
from app.services import surveys, participation


def seed(db):
    initialize(db)
    user = db.users.find_one({"username_key": "demo"})
    if user is None:
        user = {
            "_id": uid(),
            "username": "demo",
            "username_key": "demo",
            "password_hash": passwords.hash("SurveyDemo2026!"),
            "created_at": now(),
            "schema_version": 1,
        }
        db.users.insert_one(user)
    existing = db.surveys.find_one({"owner_id": user["_id"], "demo_key": "campus-v1"})
    if existing:
        return existing
    definition = json.loads(
        (ROOT / "database/examples/survey_version.json").read_text("utf-8")
    )["definition"]
    s = surveys.create(db, user, definition["title"])
    db.surveys.update_one({"_id": s["_id"]}, {"$set": {"demo_key": "campus-v1"}})
    s = surveys.save(
        db,
        s["_id"],
        user,
        SaveDraft(revision=s["revision"], draft=Definition(**definition)),
    )
    surveys.publish(db, s["_id"], user, Publish(revision=s["revision"]))
    s = db.surveys.find_one({"_id": s["_id"]})
    security = Security(settings.secret)
    samples = [
        {
            "q_role": "student",
            "q_tools": ["mongo", "python"],
            "q_hours": 6,
            "q_feedback": "希望增加更多真实案例。",
        },
        {
            "q_role": "student",
            "q_tools": ["mongo", "java"],
            "q_hours": 8,
            "q_feedback": "动手实验很有帮助。",
        },
        {"q_role": "worker", "q_hours": 4, "q_feedback": "建议增加数据建模讨论。"},
    ]
    for i, answer in enumerate(samples):
        token = participation.start(db, security, s["share_code"], user, i != 1)[
            "token"
        ]
        participation.submit(db, security, user, Submit(token=token, answers=answer))
    draft = surveys.create(db, user, "校园阅读习惯调研")
    db.surveys.update_one(
        {"_id": draft["_id"]},
        {"$set": {"draft.description": "从阅读频率到内容偏好，了解校园里的阅读日常。"}},
    )
    return s


if __name__ == "__main__":
    client = connect()
    s = seed(client[settings.database])
    print("Demo account: demo / SurveyDemo2026!")
    print("Survey path: /survey/" + s["share_code"])
