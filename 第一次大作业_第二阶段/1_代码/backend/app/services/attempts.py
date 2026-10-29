"""可恢复填写。原始输入独立于正式答案，只有校验通过的值参与路径计算。"""

import re
from itertools import pairwise

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.database import transact
from app.domain.questions import validate_answer
from app.domain.rules import evaluate, route_target
from app.errors import BusinessError, require
from app.security import now, uid
from app.services.participation import receipt
from app.services.surveys import available
from app.domain.question_sources import public_definition

NUMERIC = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$", re.ASCII)


def normalized(q, raw):
    if q["type"] == "number" and isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        require(bool(NUMERIC.fullmatch(text)), "请输入有效数字")
        try:
            return float(text)
        except (ValueError, OverflowError):
            raise BusinessError("请输入有效数字")
    return raw


def progress(definition, raw, hint=None):
    """到第一道无效题为止；无效输入不能决定分支或默认路径。"""
    qs = definition["questions"]
    positions = {q["id"]: i for i, q in enumerate(qs)}
    require(set(raw) <= set(positions), "草稿包含未知题目")
    effective, path, errors = {}, [], {}
    i = 0
    while i < len(qs):
        q = qs[i]
        path.append(q["id"])
        try:
            effective[q["id"]] = validate_answer(q, normalized(q, raw.get(q["id"])))
        except BusinessError as exc:
            errors[q["id"]] = exc.message
            break
        target = route_target(q, effective)
        if target == "END":
            break
        i = positions[target] if target else i + 1
    current = next(iter(errors), hint if hint in path else path[-1])
    return effective, path, errors, current


def owned(db, sec, user, aid, session=None):
    doc = db.attempts.find_one({"_id": aid}, session=session)
    require(doc is not None, "填写草稿不存在", 404)
    require(
        doc["respondent_key"] == sec.respondent_key(doc["survey_id"], user["_id"]),
        "填写草稿不存在",
        404,
    )
    return doc


def view(db, doc):
    survey = db.surveys.find_one({"_id": doc["survey_id"]})
    version = db.survey_versions.find_one({"_id": doc["version_id"]})
    require(
        version is not None
        and version["schema_version"] == 1
        and version["rule_engine_version"] == 1,
        "不支持的问卷版本",
        409,
    )
    reason = None
    try:
        available(survey)
    except BusinessError as exc:
        reason = exc.message
    _, path, issues, current = progress(
        version["definition"], doc["raw_answers"], doc["current_question_id"]
    )
    result = {
        k: doc[k] for k in ("_id", "revision", "status", "anonymous", "updated_at")
    }
    result.update(
        definition=public_definition(version["definition"]),
        version=version["version"],
        answers=doc["raw_answers"],
        path=path,
        issues=issues,
        current_question_id=current,
        read_only=bool(reason) or doc["status"] != "in_progress",
        read_only_reason=reason,
        deadline=survey.get("deadline") if survey else None,
    )
    if doc.get("response_id"):
        response = db.responses.find_one({"_id": doc["response_id"]})
        result["receipt"] = receipt(response)
    return result


def find_current(db, sec, user, share):
    survey = db.surveys.find_one({"share_code": share})
    require(survey is not None, "问卷不存在", 404)
    doc = db.attempts.find_one(
        {
            "survey_id": survey["_id"],
            "respondent_key": sec.respondent_key(survey["_id"], user["_id"]),
            "status": "in_progress",
        }
    )
    return view(db, doc) if doc else None


def begin(db, sec, user, share, anonymous):
    def work(session):
        survey = db.surveys.find_one_and_update(
            {"share_code": share},
            {"$inc": {"activity_seq": 1}},
            session=session,
            return_document=ReturnDocument.AFTER,
        )
        require(survey is not None, "问卷不存在", 404)
        key = sec.respondent_key(survey["_id"], user["_id"])
        existing = db.attempts.find_one(
            {
                "survey_id": survey["_id"],
                "respondent_key": key,
                "status": "in_progress",
            },
            session=session,
        )
        if existing:
            return existing
        available(survey)
        version = db.survey_versions.find_one(
            {"survey_id": survey["_id"], "version": survey["current_version"]},
            session=session,
        )
        d = version["definition"]
        require(not anonymous or d["allow_anonymous"], "此问卷不允许匿名填写")
        require(
            d["allow_repeat"]
            or db.responses.find_one(
                {"survey_id": survey["_id"], "respondent_key": key}, session=session
            )
            is None,
            "你已经提交过此问卷",
            409,
        )
        doc = {
            "_id": uid(),
            "survey_id": survey["_id"],
            "version_id": version["_id"],
            "respondent_key": key,
            "anonymous": anonymous,
            "status": "in_progress",
            "raw_answers": {},
            "current_question_id": d["questions"][0]["id"],
            "revision": 1,
            "created_at": now(),
            "updated_at": now(),
            "schema_version": 1,
        }
        db.attempts.insert_one(doc, session=session)
        return doc

    try:
        doc = transact(db, work)
    except DuplicateKeyError:
        result = find_current(db, sec, user, share)
        require(result is not None, "草稿状态已变化，请重试", 409)
        return result
    return view(db, doc)


def save(db, sec, user, aid, body):
    def work(session):
        doc = owned(db, sec, user, aid, session)
        require(doc["status"] == "in_progress", "填写已结束，不能继续保存", 409)
        require(
            doc["revision"] == body.revision, "草稿已在其他页面更新，请重新加载", 409
        )
        survey = db.surveys.find_one_and_update(
            {"_id": doc["survey_id"]},
            {"$inc": {"activity_seq": 1}},
            session=session,
            return_document=ReturnDocument.AFTER,
        )
        available(survey)
        version = db.survey_versions.find_one(
            {"_id": doc["version_id"]}, session=session
        )
        questions = {q["id"]: q for q in version["definition"]["questions"]}
        require(set(body.answers) <= set(questions), "草稿包含未知题目")
        for value in body.answers.values():
            require(
                value is None
                or type(value) in (str, int, float)
                or isinstance(value, list)
                and len(value) <= 100
                and all(isinstance(x, str) and len(x) <= 64 for x in value),
                "草稿答案结构错误",
            )
            require(
                not isinstance(value, str) or len(value) <= 20000, "草稿单项输入过长"
            )
        _, path, _, current = progress(
            version["definition"], body.answers, body.current_question_id
        )
        # 清除确定被有效跳转绕过的题目；无效前题后的暂存答案保留，修正后重新判断。
        positions = {q: i for i, q in enumerate(questions)}
        skipped = set()
        for a, b in pairwise(path):
            skipped.update(
                q for q, i in positions.items() if positions[a] < i < positions[b]
            )
        effective, _, issues, _ = progress(version["definition"], body.answers, current)
        if not issues and route_target(questions[path[-1]], effective) == "END":
            skipped.update(q for q, i in positions.items() if i > positions[path[-1]])
        raw = {k: v for k, v in body.answers.items() if k not in skipped}
        return db.attempts.find_one_and_update(
            {"_id": aid, "revision": body.revision, "status": "in_progress"},
            {
                "$set": {
                    "raw_answers": raw,
                    "current_question_id": current,
                    "updated_at": now(),
                },
                "$inc": {"revision": 1},
            },
            return_document=ReturnDocument.AFTER,
            session=session,
        )

    return view(db, transact(db, work))


def abandon(db, sec, user, aid, revision):
    doc = owned(db, sec, user, aid)
    require(doc["status"] == "in_progress", "填写已结束", 409)
    result = db.attempts.update_one(
        {"_id": aid, "revision": revision, "status": "in_progress"},
        {
            "$set": {"status": "abandoned", "raw_answers": {}, "updated_at": now()},
            "$inc": {"revision": 1},
        },
    )
    require(result.modified_count == 1, "草稿已变化，请重新加载后确认放弃", 409)
    return {"ok": True}


def submit(db, sec, user, aid, revision):
    def work(session):
        doc = owned(db, sec, user, aid, session)
        if doc["status"] == "submitted":
            return receipt(
                db.responses.find_one({"_id": doc["response_id"]}, session=session)
            )
        require(doc["status"] == "in_progress", "填写已放弃", 409)
        require(doc["revision"] == revision, "草稿已在其他页面更新，请重新加载", 409)
        survey = db.surveys.find_one_and_update(
            {"_id": doc["survey_id"]},
            {"$inc": {"activity_seq": 1}},
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        available(survey)
        version = db.survey_versions.find_one(
            {"_id": doc["version_id"]}, session=session
        )
        d = version["definition"]
        require(
            d["allow_repeat"]
            or db.responses.find_one(
                {
                    "survey_id": doc["survey_id"],
                    "respondent_key": doc["respondent_key"],
                },
                session=session,
            )
            is None,
            "你已经提交过此问卷",
            409,
        )
        raw = {}
        # 无效输入留给 evaluate 按有效路径给出逐题错误，跳过题不影响提交。
        for q in d["questions"]:
            value = doc["raw_answers"].get(q["id"])
            try:
                raw[q["id"]] = normalized(q, value)
            except BusinessError:
                raw[q["id"]] = value
        clean, path = evaluate(d, raw)
        response = {
            "_id": uid(),
            "survey_id": doc["survey_id"],
            "version_id": doc["version_id"],
            "version": version["version"],
            "attempt_id": aid,
            "respondent_key": doc["respondent_key"],
            "anonymous": doc["anonymous"],
            "answers": [{"question_id": k, "value": v} for k, v in clean.items()],
            "path": path,
            "submitted_at": now(),
            "schema_version": 1,
        }
        if not doc["anonymous"]:
            response["user_id"] = user["_id"]
        db.responses.insert_one(response, session=session)
        db.attempts.update_one(
            {"_id": aid},
            {
                "$set": {
                    "status": "submitted",
                    "raw_answers": {},
                    "response_id": response["_id"],
                    "updated_at": now(),
                },
                "$inc": {"revision": 1},
            },
            session=session,
        )
        return receipt(response)

    return transact(db, work)
