from pymongo import ReturnDocument

from app.database import transact
from app.errors import require
from app.security import now, uid
from app.services import questions


def owned(db, user, lid, session=None):
    lib = db.question_libraries.find_one(
        {"_id": lid, "owner_id": user["_id"]}, session=session
    )
    require(lib is not None, "题库不存在或无权访问", 404)
    return lib


def create(db, user, body):
    require(body.name.strip(), "题库名称不能为空")
    doc = {
        "_id": uid(),
        "owner_id": user["_id"],
        "name": body.name.strip(),
        "description": body.description,
        "revision": 1,
        "created_at": now(),
        "updated_at": now(),
        "schema_version": 1,
    }
    db.question_libraries.insert_one(doc)
    return doc


def edit(db, user, lid, body):
    require(body.name.strip(), "题库名称不能为空")
    doc = db.question_libraries.find_one_and_update(
        {"_id": lid, "owner_id": user["_id"], "revision": body.revision},
        {
            "$set": {
                "name": body.name.strip(),
                "description": body.description,
                "updated_at": now(),
            },
            "$inc": {"revision": 1},
        },
        return_document=ReturnDocument.AFTER,
    )
    require(doc is not None, "题库不存在或已变化", 409)
    return doc


def items(db, user, lid, page=1, search="", question_id=None):
    lib = owned(db, user, lid)
    query = {"library_id": lid}
    if question_id:
        query["question_id"] = question_id
    if search:
        import re

        # Search fixed version titles, only within versions this user may read.
        # Filtering happens before pagination and count; revoked private titles
        # cannot be inferred from search totals.
        owned_ids = db.questions.distinct("_id", {"owner_id": user["_id"]})
        shared_ids = db.resource_grants.distinct(
            "question_version_id",
            {"kind": "use", "active": True, "grantee_id": user["_id"]},
        )
        matching = db.question_versions.distinct(
            "_id",
            {
                "content.title": {"$regex": re.escape(search), "$options": "i"},
                "$or": [
                    {"question_id": {"$in": owned_ids}},
                    {"_id": {"$in": shared_ids}},
                ],
            },
        )
        query["question_version_id"] = {"$in": matching}
    docs = list(
        db.question_library_items.find(query)
        .sort([("position", 1), ("_id", 1)])
        .skip((page - 1) * 20)
        .limit(20)
    )
    for item in docs:
        try:
            item["version"] = questions.readable(db, user, item["question_version_id"])
            item["available"] = not db.questions.find_one({"_id": item["question_id"]})[
                "archived"
            ]
        except Exception as exc:
            from app.errors import BusinessError

            if not isinstance(exc, BusinessError):
                raise
            item["available"] = False
            item["version"] = None
    return {
        "library": lib,
        "items": docs,
        "total": db.question_library_items.count_documents(query),
        "page": page,
    }


def change_item(db, user, lid, body, item_id=None, remove=False):
    def work(s):
        lib = owned(db, user, lid, s)
        require(lib["revision"] == body.revision, "题库已变化，请刷新", 409)
        item = None
        if item_id:
            item = db.question_library_items.find_one(
                {"_id": item_id, "library_id": lid}, session=s
            )
            require(item is not None, "题库成员不存在", 404)
        if remove:
            db.question_library_items.delete_one({"_id": item_id}, session=s)
        else:
            v, _ = questions.authorize_use(db, user, body.question_version_id, s)
            require(
                item is None or item["question_id"] == v["question_id"],
                "成员升级必须选择同一题目系列",
            )
            doc = {
                "library_id": lid,
                "question_id": v["question_id"],
                "question_version_id": v["_id"],
                "position": body.position,
            }
            if item:
                db.question_library_items.update_one(
                    {"_id": item_id}, {"$set": doc}, session=s
                )
            else:
                db.question_library_items.insert_one(
                    {"_id": uid(), **doc, "created_at": now(), "schema_version": 1},
                    session=s,
                )
        db.question_libraries.update_one(
            {"_id": lid, "revision": body.revision},
            {"$inc": {"revision": 1}, "$set": {"updated_at": now()}},
            session=s,
        )
        return {"ok": True, "revision": body.revision + 1}

    return transact(db, work)
