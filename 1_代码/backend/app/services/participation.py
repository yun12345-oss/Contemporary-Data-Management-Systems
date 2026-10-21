from app.database import transact
from app.security import uid, now
from app.errors import require
from app.domain.rules import evaluate
from app.services.surveys import available


def start(db, security, share, user, anonymous):
    survey = db.surveys.find_one({"share_code": share})
    available(survey)
    version = db.survey_versions.find_one(
        {"survey_id": survey["_id"], "version": survey["current_version"]}
    )
    definition = version["definition"]
    require(not anonymous or definition["allow_anonymous"], "此问卷不允许匿名填写")
    key = security.respondent_key(survey["_id"], user["_id"])
    require(
        definition["allow_repeat"]
        or db.responses.find_one({"survey_id": survey["_id"], "respondent_key": key})
        is None,
        "你已经提交过此问卷",
        409,
    )
    return {
        "token": security.issue(survey, version, user, anonymous),
        "definition": definition,
        "version": version["version"],
        "deadline": survey.get("deadline"),
        "anonymous": anonymous,
    }


def receipt(doc):
    return {
        "id": doc["_id"],
        "version": doc["version"],
        "submitted_at": doc["submitted_at"],
    }


def submit(db, security, user, body):
    attempt = security.decode(body.token)
    require(attempt["user_id"] == user["_id"], "填写凭证不属于当前用户", 403)

    def work(session):
        previous = db.responses.find_one(
            {"attempt_id": attempt["attempt_id"]}, session=session
        )
        if previous:
            return receipt(previous)
        # 所有发布、关闭和提交均写同一问卷文档，使事务冲突可重试。
        survey = db.surveys.find_one_and_update(
            {"_id": attempt["survey_id"]},
            {"$inc": {"activity_seq": 1}},
            session=session,
            return_document=True,
        )
        available(survey)
        version = db.survey_versions.find_one(
            {"_id": attempt["version_id"], "survey_id": survey["_id"]}, session=session
        )
        require(
            version is not None
            and version["schema_version"] == 1
            and version["rule_engine_version"] == 1,
            "不支持的问卷版本",
            409,
        )
        definition = version["definition"]
        require(
            not attempt["anonymous"] or definition["allow_anonymous"], "匿名设置无效"
        )
        key = security.respondent_key(survey["_id"], user["_id"])
        require(
            definition["allow_repeat"]
            or db.responses.find_one(
                {"survey_id": survey["_id"], "respondent_key": key}, session=session
            )
            is None,
            "你已经提交过此问卷",
            409,
        )
        clean, path = evaluate(definition, body.answers)
        doc = {
            "_id": uid(),
            "survey_id": survey["_id"],
            "version_id": version["_id"],
            "version": version["version"],
            "attempt_id": attempt["attempt_id"],
            "respondent_key": key,
            "anonymous": attempt["anonymous"],
            "answers": [
                {"question_id": qid, "value": value} for qid, value in clean.items()
            ],
            "path": path,
            "submitted_at": now(),
            "schema_version": 1,
        }
        if not attempt["anonymous"]:
            doc["user_id"] = user["_id"]
        db.responses.insert_one(doc, session=session)
        return receipt(doc)

    return transact(db, work)
