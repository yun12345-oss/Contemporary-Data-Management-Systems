from app.errors import require


def usage(db, user, qid, page=1):
    q = db.questions.find_one({"_id": qid})
    require(q is not None, "题目不存在或无权访问", 404)
    mine = q["owner_id"] == user["_id"]
    if not mine:
        # Current or former lawful users can inspect their own survey use only.
        has_grant = db.resource_grants.find_one(
            {
                "kind": "use",
                "question_version_id": {
                    "$in": db.question_versions.distinct("_id", {"question_id": qid})
                },
                "grantee_id": user["_id"],
            }
        )
        require(has_grant is not None, "无权查看使用情况", 404)
    draft_query = {"draft.questions.source.question_id": qid}
    pub_query = {"definition.questions.source.question_id": qid}
    own_ids = db.surveys.distinct("_id", {"owner_id": user["_id"]})
    if not mine:
        draft_query["owner_id"] = user["_id"]
        pub_query["survey_id"] = {"$in": own_ids}
    draft_ids = set(db.surveys.distinct("_id", draft_query))
    historical = set(db.survey_versions.distinct("survey_id", pub_query))
    all_ids = draft_ids | historical
    current_ids = set()
    # Aggregate only identifiers/counts for others; their titles/details are never returned.
    current_pipeline = [
        {"$match": pub_query},
        {
            "$lookup": {
                "from": "surveys",
                "localField": "survey_id",
                "foreignField": "_id",
                "as": "s",
            }
        },
        {"$unwind": "$s"},
        {"$match": {"$expr": {"$eq": ["$version", "$s.current_version"]}}},
        {"$group": {"_id": "$survey_id"}},
    ]
    current_ids = {d["_id"] for d in db.survey_versions.aggregate(current_pipeline)}
    visible = (
        db.surveys.find({"_id": {"$in": list(all_ids)}, "owner_id": user["_id"]})
        .sort("created_at", -1)
        .skip((page - 1) * 20)
        .limit(20)
    )
    rows = []
    for s in visible:
        versions = list(
            db.survey_versions.find(
                {"survey_id": s["_id"], "definition.questions.source.question_id": qid},
                {"definition": 0},
            ).sort("version", -1)
        )
        rows.append(
            {
                "survey_id": s["_id"],
                "title": s["draft"]["title"],
                "status": s["status"],
                "draft": s["_id"] in draft_ids,
                "current_published": s["_id"] in current_ids,
                "published_versions": [v["version"] for v in versions],
            }
        )
    return {
        "scope": "题目所有者脱敏汇总及自有详情" if mine else "仅自有问卷",
        "used_surveys": len(all_ids),
        "draft_surveys": len(draft_ids),
        "current_published_surveys": len(current_ids),
        "historical_published_surveys": len(historical),
        "items": rows,
        "page": page,
        "detail_total": len(all_ids & set(own_ids)),
    }
