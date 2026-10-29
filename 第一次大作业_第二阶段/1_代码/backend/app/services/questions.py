from copy import deepcopy

from pymongo import ReturnDocument

from app.database import transact
from app.domain.question_versions import check_content, diff
from app.errors import require
from app.security import now, uid


def owned(db, user, qid, session=None):
    q = db.questions.find_one({"_id": qid, "owner_id": user["_id"]}, session=session)
    require(q is not None, "题目不存在或无权操作", 404)
    return q


def version(db, vid, session=None):
    v = db.question_versions.find_one({"_id": vid}, session=session)
    require(v is not None, "题目版本不存在或无权访问", 404)
    return v


def readable(db, user, vid, session=None):
    v = version(db, vid, session)
    q = db.questions.find_one({"_id": v["question_id"]}, session=session)
    require(q is not None, "题目不存在", 404)
    if q["owner_id"] != user["_id"]:
        grant = db.resource_grants.find_one(
            {
                "kind": "use",
                "question_version_id": vid,
                "grantee_id": user["_id"],
                "active": True,
            },
            session=session,
        )
        require(grant is not None, "无权访问此题目版本", 404)
    return v


def authorize_use(db, user, vid, session):
    """Touch both coordination records: revocation/archive race with this write."""
    v = version(db, vid, session)
    q = db.questions.find_one_and_update(
        {"_id": v["question_id"], "archived": False},
        {"$inc": {"activity_seq": 1}},
        session=session,
        return_document=ReturnDocument.AFTER,
    )
    require(q is not None, "题目已归档，不能新增使用", 409)
    gid = None
    if q["owner_id"] != user["_id"]:
        g = db.resource_grants.find_one_and_update(
            {
                "kind": "use",
                "question_version_id": vid,
                "grantee_id": user["_id"],
                "active": True,
            },
            {"$inc": {"activity_seq": 1}},
            session=session,
            return_document=ReturnDocument.AFTER,
        )
        require(g is not None, "当前没有此版本的使用授权", 403)
        gid = g["_id"]
    return v, gid


def create(db, user, content, note="创建题目", session=None):
    content = check_content(deepcopy(content))
    qid, vid, stamp = uid(), uid(), now()
    q = {
        "_id": qid,
        "owner_id": user["_id"],
        "title": content["title"],
        "latest_version_id": vid,
        "version_seq": 1,
        "revision": 1,
        "archived": False,
        "activity_seq": 0,
        "created_at": stamp,
        "updated_at": stamp,
        "schema_version": 1,
    }
    v = {
        "_id": vid,
        "question_id": qid,
        "version": 1,
        "parent_version_id": None,
        "restored_from_version_id": None,
        "content": content,
        "change_note": note,
        "created_by": user["_id"],
        "created_at": stamp,
        "schema_version": 1,
    }

    def work(s):
        db.questions.insert_one(q, session=s)
        db.question_versions.insert_one(v, session=s)
        return {"question": q, "version": v}

    return work(session) if session else transact(db, work)


def new_version(db, user, qid, body, restore=False):
    def work(s):
        q = owned(db, user, qid, s)
        require(not q["archived"], "已归档题目不能创建版本", 409)
        require(q["revision"] == body.revision, "题目已变化，请刷新后重试", 409)
        parent = version(db, body.parent_version_id, s)
        require(parent["question_id"] == qid, "父版本不属于此题目")
        source = version(db, body.restored_from_version_id, s) if restore else None
        require(source is None or source["question_id"] == qid, "恢复来源不属于此题目")
        content = check_content(
            deepcopy(source["content"] if restore else body.content.model_dump())
        )
        v = {
            "_id": uid(),
            "question_id": qid,
            "version": q["version_seq"] + 1,
            "parent_version_id": parent["_id"],
            "restored_from_version_id": source["_id"] if source else None,
            "content": content,
            "change_note": body.change_note,
            "created_by": user["_id"],
            "created_at": now(),
            "schema_version": 1,
        }
        updated = db.questions.find_one_and_update(
            {"_id": qid, "revision": body.revision},
            {
                "$set": {
                    "latest_version_id": v["_id"],
                    "title": content["title"],
                    "updated_at": now(),
                },
                "$inc": {"version_seq": 1, "revision": 1, "activity_seq": 1},
            },
            session=s,
            return_document=ReturnDocument.AFTER,
        )
        require(updated is not None, "题目已变化", 409)
        db.question_versions.insert_one(v, session=s)
        return {
            "question": updated,
            "version": v,
            "diff": diff(parent["content"], content),
        }

    return transact(db, work)


def archive(db, user, qid, revision):
    owned(db, user, qid)
    q = db.questions.find_one_and_update(
        {"_id": qid, "revision": revision},
        {
            "$set": {"archived": True, "updated_at": now()},
            "$inc": {"revision": 1, "activity_seq": 1},
        },
        return_document=ReturnDocument.AFTER,
    )
    require(q is not None, "题目已变化，请刷新", 409)
    return q


def listing(db, user, page=1, search="", question_id=None):
    # Exact-version sharing: do not expose other versions of another owner's series.
    shared = db.resource_grants.distinct(
        "question_version_id",
        {"kind": "use", "active": True, "grantee_id": user["_id"]},
    )
    query = {
        "$or": [
            {"owner_id": user["_id"]},
            {
                "_id": {
                    "$in": db.question_versions.distinct(
                        "question_id", {"_id": {"$in": shared}}
                    )
                }
            },
        ]
    }
    if search:
        import re

        # Search owned titles or accessible version content, not private future-version titles.
        matched = db.question_versions.distinct(
            "question_id",
            {
                "content.title": {"$regex": re.escape(search), "$options": "i"},
                "$or": [
                    {"_id": {"$in": shared}},
                    {
                        "question_id": {
                            "$in": db.questions.distinct(
                                "_id", {"owner_id": user["_id"]}
                            )
                        }
                    },
                ],
            },
        )
        query["_id"] = {"$in": matched}
    if question_id:
        query.setdefault("$and", []).append({"_id": question_id})
    docs = list(
        db.questions.find(query).sort("updated_at", -1).skip((page - 1) * 20).limit(20)
    )
    items = []
    for q in docs:
        mine = q["owner_id"] == user["_id"]
        vs = list(
            db.question_versions.find(
                {"question_id": q["_id"], **({} if mine else {"_id": {"$in": shared}})}
            ).sort("version", -1)
        )
        items.append(
            {
                "_id": q["_id"],
                "owner_id": q["owner_id"],
                "owned": mine,
                "archived": q["archived"],
                "revision": q["revision"] if mine else None,
                "title": vs[0]["content"]["title"],
                "versions": vs,
                "latest_version_id": q["latest_version_id"] if mine else None,
            }
        )
    return {"items": items, "total": db.questions.count_documents(query), "page": page}
