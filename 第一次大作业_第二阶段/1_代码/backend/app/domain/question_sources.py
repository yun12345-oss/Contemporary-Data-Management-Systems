from copy import deepcopy

from app.domain.question_versions import content_of
from app.errors import require


def check_sources(db, survey, incoming, session=None):
    ids = [q["id"] for q in incoming["questions"]]
    require(
        len(ids) == len(set(ids)) and "END" not in ids, "题目实例 ID 不能重复或为 END"
    )
    original = {q["id"]: q for q in survey["draft"]["questions"]}
    for q in incoming["questions"]:
        src = q.get("source")
        old = original.get(q["id"], {}).get("source")
        require(src == old, "题目来源只能通过导入、升级或解除关联操作修改", 403)
        if src:
            require(
                src["survey_id"] == survey["_id"]
                and src["instance_id"] == q["id"]
                and src["imported_by"] == survey["owner_id"],
                "导入凭据不属于此实例",
                403,
            )
            v = db.question_versions.find_one(
                {
                    "_id": src["question_version_id"],
                    "question_id": src["question_id"],
                    "version": src["version"],
                },
                session=session,
            )
            require(
                v is not None and content_of(q) == v["content"],
                "题目内容与来源版本不一致，请创建新版本或执行允许的解除关联操作",
                403,
            )
    return incoming


def source_for(survey, user, instance, v, gid):
    from app.security import now

    return {
        "question_id": v["question_id"],
        "question_version_id": v["_id"],
        "version": v["version"],
        "survey_id": survey["_id"],
        "instance_id": instance,
        "imported_by": user["_id"],
        "imported_at": now(),
        "grant_id": gid,
    }


def public_definition(definition):
    result = deepcopy(definition)
    for q in result["questions"]:
        q.pop("source", None)
    return result
