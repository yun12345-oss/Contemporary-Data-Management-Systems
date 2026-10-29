from copy import deepcopy

from pymongo import ReturnDocument

from app.database import transact
from app.domain.question_sources import check_sources, source_for
from app.domain.question_versions import content_of, definition_issues, diff
from app.errors import require
from app.security import now, uid
from app.services import questions, surveys


def commit(db, survey, draft, session):
    issues = definition_issues(draft)
    result = db.surveys.find_one_and_update(
        {"_id": survey["_id"], "revision": survey["revision"]},
        {
            "$set": {"draft": draft, "draft_issues": issues, "updated_at": now()},
            "$inc": {"revision": 1},
        },
        session=session,
        return_document=ReturnDocument.AFTER,
    )
    require(result is not None, "问卷已变化，请先保存并刷新", 409)
    return result


def operation(db, user, sid, body, kind, preview=False):
    def work(s):
        survey = surveys.owned(db, sid, user, s)
        require(survey["revision"] == body.revision, "问卷已变化，请先保存并刷新", 409)
        draft = deepcopy(survey["draft"])
        if kind == "import":
            require(len(draft["questions"]) < 100, "每份问卷最多100题")
            v, gid = questions.authorize_use(db, user, body.question_version_id, s)
            iid = uid()
            draft["questions"].append(
                {
                    "id": iid,
                    **deepcopy(v["content"]),
                    "required": True,
                    "routing": {"rules": [], "default_target": None},
                    "source": source_for(survey, user, iid, v, gid),
                }
            )
        else:
            q = next(
                (x for x in draft["questions"] if x["id"] == body.instance_id), None
            )
            require(q is not None, "问卷实例不存在", 404)
            src = q.get("source")
            if kind == "save-question":
                check_sources(db, survey, draft, s)
                if src:
                    questions.owned(db, user, src["question_id"], s)
                # Shared instances cannot be turned into a new owned series.
                created = questions.create(db, user, content_of(q), "从自有问卷保存", s)
                v = created["version"]
                q["source"] = source_for(survey, user, q["id"], v, None)
                result = commit(db, survey, draft, s)
                return {"survey": result, **created}
            require(src is not None, "此题没有来源", 409)
            if kind == "detach":
                questions.owned(db, user, src["question_id"], s)
                q.pop("source", None)
            elif kind == "upgrade":
                # Preview does not confer use rights; final operation always rechecks and touches grants.
                if preview:
                    v = questions.readable(db, user, body.question_version_id, s)
                    gid = None
                else:
                    v, gid = questions.authorize_use(
                        db, user, body.question_version_id, s
                    )
                require(
                    v["question_id"] == src["question_id"],
                    "升级目标必须属于同一题目系列",
                )
                changes = diff(content_of(q), v["content"])
                q.update(deepcopy(v["content"]))
                q["source"] = source_for(survey, user, q["id"], v, gid)
                if preview:
                    return {
                        "diff": changes,
                        "issues": definition_issues(draft),
                        "definition": draft,
                    }
        return commit(db, survey, draft, s)

    return transact(db, work)
