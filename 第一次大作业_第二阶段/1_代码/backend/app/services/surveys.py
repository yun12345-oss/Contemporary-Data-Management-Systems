from pymongo import ReturnDocument

from app.database import transact
from app.domain.question_sources import check_sources
from app.domain.question_versions import definition_issues
from app.domain.rules import check_definition
from app.errors import require
from app.security import now, uid


def owned(db, survey_id, user, session=None):
    doc = db.surveys.find_one(
        {"_id": survey_id, "owner_id": user["_id"]}, session=session
    )
    require(doc is not None, "问卷不存在或无权访问", 404)
    return doc


def create(db, user, title):
    doc = {
        "_id": uid(),
        "owner_id": user["_id"],
        "share_code": uid(),
        "status": "draft",
        "draft": {
            "title": title,
            "description": "",
            "allow_anonymous": False,
            "allow_repeat": False,
            "questions": [],
        },
        "deadline": None,
        "revision": 1,
        "current_version": 0,
        "created_at": now(),
        "updated_at": now(),
        "schema_version": 1,
        "activity_seq": 0,
    }
    db.surveys.insert_one(doc)
    return doc


def save(db, survey_id, user, body):
    def work(session):
        survey = owned(db, survey_id, user, session)
        require(
            survey["revision"] == body.revision,
            "草稿已被其他窗口修改，请刷新后重试",
            409,
        )
        draft = body.draft.model_dump()
        for q in draft["questions"]:
            if q.get("source") is None:
                q.pop("source", None)
        check_sources(db, survey, draft, session)
        updated = db.surveys.find_one_and_update(
            {"_id": survey_id, "owner_id": user["_id"], "revision": body.revision},
            {
                "$set": {
                    "draft": draft,
                    "draft_issues": definition_issues(draft),
                    "updated_at": now(),
                },
                "$inc": {"revision": 1},
            },
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        require(updated is not None, "草稿已被其他窗口修改，请刷新后重试", 409)
        return updated

    return transact(db, work)


def publish(db, survey_id, user, body):
    def work(session):
        survey = owned(db, survey_id, user, session)
        require(
            survey["revision"] == body.revision, "问卷已经变化，请刷新后再发布", 409
        )
        require(
            body.deadline is None or body.deadline > now(), "截止时间必须晚于当前时间"
        )
        check_sources(db, survey, survey["draft"], session)
        check_definition(survey["draft"])
        version = {
            "_id": uid(),
            "survey_id": survey_id,
            "version": survey["current_version"] + 1,
            "definition": survey["draft"],
            "published_at": now(),
            "schema_version": 1,
            "rule_engine_version": 1,
        }
        db.survey_versions.insert_one(version, session=session)
        updated = db.surveys.find_one_and_update(
            {"_id": survey_id},
            {
                "$set": {
                    "status": "published",
                    "deadline": body.deadline,
                    "current_version": version["version"],
                    "updated_at": now(),
                },
                "$inc": {"revision": 1, "activity_seq": 1},
            },
            session=session,
            return_document=ReturnDocument.AFTER,
        )
        return {**version, "survey": survey_metadata(updated)}

    return transact(db, work)


def survey_metadata(survey):
    return {
        key: survey[key]
        for key in ("revision", "status", "current_version", "deadline", "updated_at")
    }


def available(survey):
    require(survey is not None, "问卷不存在", 404)
    require(survey["status"] == "published", "问卷尚未发布或已经关闭", 409)
    require(
        survey.get("deadline") is None or survey["deadline"] > now(), "问卷已截止", 409
    )
