"""两阶段分组去重，不将全部填写者 ID 聚合进一个大数组。"""


def population(db, pipeline):
    rows = list(
        db.responses.aggregate(
            pipeline
            + [
                {"$group": {"_id": "$respondent_key", "n": {"$sum": 1}}},
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": "$n"},
                        "respondent_count": {"$sum": 1},
                    }
                },
            ]
        )
    )
    return rows[0] if rows else {"total": 0, "respondent_count": 0}


def option_counts(db, pipeline, options):
    rows = db.responses.aggregate(
        pipeline
        + [
            {
                "$group": {
                    "_id": {"option": "$answers.value", "person": "$respondent_key"},
                    "n": {"$sum": 1},
                }
            },
            {
                "$group": {
                    "_id": "$_id.option",
                    "count": {"$sum": "$n"},
                    "respondent_count": {"$sum": 1},
                }
            },
        ]
    )
    counts = {r["_id"]: r for r in rows}
    return [
        {
            **o,
            "count": counts.get(o["id"], {}).get("count", 0),
            "respondent_count": counts.get(o["id"], {}).get("respondent_count", 0),
        }
        for o in options
    ]
