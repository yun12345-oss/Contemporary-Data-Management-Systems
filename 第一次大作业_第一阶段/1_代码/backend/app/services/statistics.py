from app.errors import require
from app.services.surveys import owned
from app.domain.questions import handler
from app.aggregation import population


def select_version(db, sid, user, version):
    survey = owned(db, sid, user)
    doc = db.survey_versions.find_one(
        {"survey_id": sid, "version": version or survey["current_version"]}
    )
    require(doc is not None, "尚无对应发布版本", 404)
    return doc


def query_filter(sid, version, start=None, end=None):
    require(not start or not end or start <= end, "开始时间不能晚于结束时间")
    match = {"survey_id": sid, "version": version}
    if start or end:
        match["submitted_at"] = {}
        if start:
            match["submitted_at"]["$gte"] = start
        if end:
            match["submitted_at"]["$lte"] = end
    return match


def aggregate(db, sid, user, version=None, start=None, end=None):
    ver = select_version(db, sid, user, version)
    match = query_filter(sid, ver["version"], start, end)
    totals = population(db, [{"$match": match}])
    questions = []
    for q in ver["definition"]["questions"]:
        base = [
            {"$match": match},
            {"$unwind": "$answers"},
            {
                "$match": {
                    "answers.question_id": q["id"],
                    "answers.value": {"$ne": None},
                }
            },
        ]
        counts = population(db, base)
        item = {
            "id": q["id"],
            "title": q["title"],
            "type": q["type"],
            "answered": counts["total"],
            "respondent_count": counts["respondent_count"],
        }
        item.update(handler(q["type"]).summarize(db, base, q))
        questions.append(item)
    return {
        "version": ver["version"],
        "title": ver["definition"]["title"],
        "total": totals["total"],
        "respondent_count": totals["respondent_count"],
        "questions": questions,
    }


def values(db, sid, user, qid, version=None, page=1, start=None, end=None):
    ver = select_version(db, sid, user, version)
    require(
        any(q["id"] == qid for q in ver["definition"]["questions"]), "题目不存在", 404
    )
    match = query_filter(sid, ver["version"], start, end)
    base = [
        {"$match": match},
        {"$unwind": "$answers"},
        {"$match": {"answers.question_id": qid, "answers.value": {"$ne": None}}},
    ]
    counts = list(db.responses.aggregate(base + [{"$count": "n"}]))
    # 白名单输出，不向创建者返回会话、匿名去重标识或匿名用户身份。
    rows = list(
        db.responses.aggregate(
            base
            + [
                {"$sort": {"submitted_at": -1, "_id": 1}},
                {"$skip": (page - 1) * 20},
                {"$limit": 20},
                {
                    "$project": {
                        "_id": 0,
                        "value": "$answers.value",
                        "submitted_at": 1,
                        "anonymous": 1,
                        "user_id": 1,
                    }
                },
            ]
        )
    )
    return {
        "items": rows,
        "total": counts[0]["n"] if counts else 0,
        "page": page,
        "page_size": 20,
    }
