from app.errors import require
from app.services import questions


def aggregate(db, user, vid, start=None, end=None, survey_id=None, boundaries=None):
    v = questions.version(db, vid)
    require(start is None or start.tzinfo is not None, "时间必须包含时区")
    require(end is None or end.tzinfo is not None, "时间必须包含时区")
    require(not start or not end or start <= end, "开始时间不能晚于结束时间")
    from app.domain.numbers import safe_number

    if boundaries is None:
        boundaries = [0, 18, 30, 45, 60, 121]
    require(
        all(safe_number(x) for x in boundaries),
        "分组边界必须是有限数值，且绝对值不超过 10¹⁵",
    )
    require(
        2 <= len(boundaries) <= 30
        and all(type(x) in (int, float) for x in boundaries)
        and all(a < b for a, b in zip(boundaries, boundaries[1:])),
        "分组边界需严格递增，最多30项",
    )
    own = db.surveys.distinct("_id", {"owner_id": user["_id"]})
    granted = db.resource_grants.distinct(
        "survey_id",
        {
            "kind": "aggregate",
            "question_version_id": vid,
            "grantee_id": user["_id"],
            "active": True,
        },
    )
    allowed = set(own) | set(granted)
    if survey_id:
        require(survey_id in allowed, "无权统计此问卷", 403)
        allowed = {survey_id}
    published = db.survey_versions.distinct(
        "survey_id",
        {
            "survey_id": {"$in": list(allowed)},
            "definition.questions.source.question_version_id": vid,
        },
    )
    q = db.questions.find_one({"_id": v["question_id"]})
    require(
        q["owner_id"] == user["_id"] or bool(published) or bool(granted),
        "无权查看此题目统计",
        404,
    )
    # Authorization is applied before any answer aggregation. No global respondent keys are used.
    match = {"survey_id": {"$in": published}}
    if start or end:
        match["submitted_at"] = {}
        if start:
            match["submitted_at"]["$gte"] = start
        if end:
            match["submitted_at"]["$lte"] = end
    base = [
        {"$match": match},
        {
            "$lookup": {
                "from": "survey_versions",
                "localField": "version_id",
                "foreignField": "_id",
                "as": "snapshot",
            }
        },
        {"$unwind": "$snapshot"},
        {
            "$set": {
                "instances": {
                    "$filter": {
                        "input": "$snapshot.definition.questions",
                        "as": "q",
                        "cond": {
                            "$eq": [
                                {"$ifNull": ["$$q.source.question_version_id", None]},
                                vid,
                            ]
                        },
                    }
                }
            }
        },
        {"$unwind": "$answers"},
        {
            "$match": {
                "answers.value": {"$ne": None},
                "$expr": {"$in": ["$answers.question_id", "$instances.id"]},
            }
        },
    ]
    facets = {
        "answers": [{"$count": "n"}],
        "responses": [{"$group": {"_id": "$_id"}}, {"$count": "n"}],
        "surveys": [{"$group": {"_id": "$survey_id"}}, {"$count": "n"}],
    }
    content = v["content"]
    if content["type"] in ("single_choice", "multiple_choice"):
        facets["options"] = (
            [{"$unwind": "$answers.value"}]
            if content["type"] == "multiple_choice"
            else []
        ) + [{"$group": {"_id": "$answers.value", "count": {"$sum": 1}}}]
    if content["type"] == "number":
        facets["numbers"] = [
            {
                "$group": {
                    "_id": None,
                    "average": {"$avg": "$answers.value"},
                    "min": {"$min": "$answers.value"},
                    "max": {"$max": "$answers.value"},
                }
            }
        ]
        facets["distribution"] = [
            {
                "$bucket": {
                    "groupBy": "$answers.value",
                    "boundaries": boundaries,
                    "default": "outside",
                    "output": {"count": {"$sum": 1}},
                }
            }
        ]
    data = list(db.responses.aggregate(base + [{"$facet": facets}]))[0]
    count = lambda k: data[k][0]["n"] if data[k] else 0
    total = count("answers")
    out = {
        "question_id": v["question_id"],
        "question_version_id": vid,
        "version": v["version"],
        "content": content,
        "coverage_surveys": len(published),
        "answered_surveys": count("surveys"),
        "valid_responses": count("responses"),
        "valid_answers": total,
        "notice": "仅同一确定版本；授权范围内汇总；作答条数按实例计，答卷按记录去重；必答与路径可能影响样本。",
    }
    if "options" in data:
        counts = {x["_id"]: x["count"] for x in data["options"]}
        out["options"] = [
            {
                **o,
                "count": counts.get(o["id"], 0),
                "ratio": counts.get(o["id"], 0) / total if total else 0,
            }
            for o in content["options"]
        ]
    if "numbers" in data:
        out.update(
            {
                k: (data["numbers"][0][k] if data["numbers"] else None)
                for k in ["average", "min", "max"]
            }
        )
        bins = {x["_id"]: x["count"] for x in data["distribution"]}
        out["distribution"] = [
            {"lower": a, "upper": b, "count": bins.get(a, 0)}
            for a, b in zip(boundaries, boundaries[1:])
        ] + [{"label": "区间外", "count": bins.get("outside", 0)}]
    return out
