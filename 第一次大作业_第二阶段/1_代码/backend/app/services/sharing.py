from pymongo import ReturnDocument

from app.database import transact
from app.errors import require
from app.security import now, uid
from app.services import questions, surveys


def grant(db, user, body):
    def work(s):
        v = questions.version(db, body.question_version_id, s)
        target = db.users.find_one(
            {"username_key": body.username.casefold()}, session=s
        )
        require(target is not None, "接收账号不存在", 404)
        require(target["_id"] != user["_id"], "无需给自己授权")
        sid = body.survey_id
        if body.kind == "use":
            require(sid is None, "使用授权不能指定问卷")
            q = questions.owned(db, user, v["question_id"], s)
            require(not q["archived"], "已归档题目不能新增授权", 409)
            db.questions.update_one(
                {"_id": q["_id"]}, {"$inc": {"activity_seq": 1}}, session=s
            )
        else:
            require(sid is not None, "汇总授权必须指定问卷")
            surveys.owned(db, sid, user, s)
            require(
                db.survey_versions.find_one(
                    {
                        "survey_id": sid,
                        "definition.questions.source.question_version_id": v["_id"],
                    },
                    session=s,
                )
                is not None,
                "该问卷没有发布使用此题目版本",
                409,
            )
            db.surveys.update_one(
                {"_id": sid}, {"$inc": {"activity_seq": 1}}, session=s
            )
        query = {
            "kind": body.kind,
            "question_version_id": v["_id"],
            "survey_id": sid,
            "grantee_id": target["_id"],
        }
        g = db.resource_grants.find_one(query, session=s)
        if g:
            return db.resource_grants.find_one_and_update(
                {"_id": g["_id"]},
                {
                    "$set": {"active": True, "updated_at": now()},
                    "$inc": {"revision": 1, "activity_seq": 1},
                },
                return_document=ReturnDocument.AFTER,
                session=s,
            )
        g = {
            "_id": uid(),
            **query,
            "grantor_id": user["_id"],
            "active": True,
            "revision": 1,
            "activity_seq": 0,
            "created_at": now(),
            "updated_at": now(),
            "schema_version": 1,
        }
        db.resource_grants.insert_one(g, session=s)
        return g

    return transact(db, work)


def revoke(db, user, gid, revision):
    g = db.resource_grants.find_one_and_update(
        {"_id": gid, "grantor_id": user["_id"], "revision": revision},
        {
            "$set": {"active": False, "updated_at": now()},
            "$inc": {"revision": 1, "activity_seq": 1},
        },
        return_document=ReturnDocument.AFTER,
    )
    require(g is not None, "授权不存在或已变化", 409)
    return g


def listing(db, user, page=1):
    query = {"$or": [{"grantor_id": user["_id"]}, {"grantee_id": user["_id"]}]}
    docs = list(
        db.resource_grants.find(query)
        .sort("updated_at", -1)
        .skip((page - 1) * 20)
        .limit(20)
    )
    for g in docs:
        for key in ["grantor_id", "grantee_id"]:
            u = db.users.find_one({"_id": g[key]}, {"username": 1})
            g[key.replace("_id", "_username")] = u["username"] if u else "已不存在账号"
    return {
        "items": docs,
        "total": db.resource_grants.count_documents(query),
        "page": page,
    }
