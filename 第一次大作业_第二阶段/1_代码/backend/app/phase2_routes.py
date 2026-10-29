"""Second-stage routes reuse the first-stage auth, database and error boundary."""

from datetime import datetime

from fastapi import Depends, Query

from app import schemas as S
from app.domain.question_versions import diff
from app.services import (
    libraries,
    question_instances,
    question_statistics,
    question_usage,
    questions,
    sharing,
)


def register(app, db, current_user):
    @app.get("/api/questions")
    def question_list(
        page: int = Query(1, ge=1),
        search: str = Query("", max_length=200),
        question_id: str | None = Query(None, max_length=64),
        database=Depends(db),
        user=Depends(current_user),
    ):
        return questions.listing(database, user, page, search, question_id)

    @app.post("/api/questions", status_code=201)
    def question_create(
        body: S.NewQuestion, database=Depends(db), user=Depends(current_user)
    ):
        return questions.create(
            database, user, body.content.model_dump(), body.change_note
        )

    @app.get("/api/questions/{qid}")
    def question_get(qid: str, database=Depends(db), user=Depends(current_user)):
        q = questions.owned(database, user, qid)
        return {
            "question": q,
            "versions": list(
                database.question_versions.find({"question_id": qid}).sort(
                    "version", -1
                )
            ),
        }

    @app.get("/api/question-versions/{vid}")
    def version_get(vid: str, database=Depends(db), user=Depends(current_user)):
        return questions.readable(database, user, vid)

    @app.get("/api/question-versions/{vid}/diff/{other}")
    def version_diff(
        vid: str, other: str, database=Depends(db), user=Depends(current_user)
    ):
        a = questions.readable(database, user, vid)
        b = questions.readable(database, user, other)
        from app.errors import require

        require(a["question_id"] == b["question_id"], "只能比较同一题目系列")
        return diff(a["content"], b["content"])

    @app.post("/api/questions/{qid}/versions", status_code=201)
    def version_create(
        qid: str,
        body: S.NewQuestionVersion,
        database=Depends(db),
        user=Depends(current_user),
    ):
        return questions.new_version(database, user, qid, body)

    @app.post("/api/questions/{qid}/restore", status_code=201)
    def version_restore(
        qid: str,
        body: S.RestoreQuestion,
        database=Depends(db),
        user=Depends(current_user),
    ):
        return questions.new_version(database, user, qid, body, True)

    @app.post("/api/questions/{qid}/archive")
    def question_archive(
        qid: str, body: S.Revision, database=Depends(db), user=Depends(current_user)
    ):
        return questions.archive(database, user, qid, body.revision)

    @app.get("/api/questions/{qid}/usage")
    def usage(
        qid: str,
        page: int = Query(1, ge=1),
        database=Depends(db),
        user=Depends(current_user),
    ):
        return question_usage.usage(database, user, qid, page)

    @app.get("/api/question-versions/{vid}/statistics")
    def stats(
        vid: str,
        start: datetime | None = None,
        end: datetime | None = None,
        survey_id: str | None = None,
        boundaries: list[float] | None = Query(None),
        database=Depends(db),
        user=Depends(current_user),
    ):
        return question_statistics.aggregate(
            database, user, vid, start, end, survey_id, boundaries
        )

    @app.post("/api/grants", status_code=201)
    def grant(body: S.GrantRequest, database=Depends(db), user=Depends(current_user)):
        return sharing.grant(database, user, body)

    @app.get("/api/grants")
    def grants(
        page: int = Query(1, ge=1), database=Depends(db), user=Depends(current_user)
    ):
        return sharing.listing(database, user, page)

    @app.post("/api/grants/{gid}/revoke")
    def revoke(
        gid: str, body: S.Revision, database=Depends(db), user=Depends(current_user)
    ):
        return sharing.revoke(database, user, gid, body.revision)

    @app.get("/api/libraries")
    def library_list(
        page: int = Query(1, ge=1), database=Depends(db), user=Depends(current_user)
    ):
        query = {"owner_id": user["_id"]}
        return {
            "items": list(
                database.question_libraries.find(query)
                .sort("updated_at", -1)
                .skip((page - 1) * 20)
                .limit(20)
            ),
            "total": database.question_libraries.count_documents(query),
            "page": page,
        }

    @app.post("/api/libraries", status_code=201)
    def library_create(
        body: S.LibraryRequest, database=Depends(db), user=Depends(current_user)
    ):
        return libraries.create(database, user, body)

    @app.put("/api/libraries/{lid}")
    def library_edit(
        lid: str, body: S.EditLibrary, database=Depends(db), user=Depends(current_user)
    ):
        return libraries.edit(database, user, lid, body)

    @app.get("/api/libraries/{lid}/items")
    def library_items(
        lid: str,
        page: int = Query(1, ge=1),
        search: str = Query("", max_length=200),
        question_id: str | None = Query(None, max_length=64),
        database=Depends(db),
        user=Depends(current_user),
    ):
        return libraries.items(database, user, lid, page, search, question_id)

    @app.post("/api/libraries/{lid}/items", status_code=201)
    def item_add(
        lid: str,
        body: S.LibraryItemRequest,
        database=Depends(db),
        user=Depends(current_user),
    ):
        return libraries.change_item(database, user, lid, body)

    @app.put("/api/libraries/{lid}/items/{iid}")
    def item_edit(
        lid: str,
        iid: str,
        body: S.UpdateLibraryItem,
        database=Depends(db),
        user=Depends(current_user),
    ):
        return libraries.change_item(database, user, lid, body, iid)

    @app.post("/api/libraries/{lid}/items/{iid}/remove")
    def item_remove(
        lid: str,
        iid: str,
        body: S.Revision,
        database=Depends(db),
        user=Depends(current_user),
    ):
        return libraries.change_item(database, user, lid, body, iid, True)

    @app.post("/api/surveys/{sid}/questions/import")
    def import_question(
        sid: str,
        body: S.ImportQuestion,
        database=Depends(db),
        user=Depends(current_user),
    ):
        return question_instances.operation(database, user, sid, body, "import")

    @app.post("/api/surveys/{sid}/questions/upgrade-preview")
    def preview_question(
        sid: str,
        body: S.UpgradeQuestion,
        database=Depends(db),
        user=Depends(current_user),
    ):
        return question_instances.operation(database, user, sid, body, "upgrade", True)

    @app.post("/api/surveys/{sid}/questions/upgrade")
    def upgrade_question(
        sid: str,
        body: S.UpgradeQuestion,
        database=Depends(db),
        user=Depends(current_user),
    ):
        return question_instances.operation(database, user, sid, body, "upgrade")

    @app.post("/api/surveys/{sid}/questions/detach")
    def detach_question(
        sid: str,
        body: S.InstanceOperation,
        database=Depends(db),
        user=Depends(current_user),
    ):
        return question_instances.operation(database, user, sid, body, "detach")

    @app.post("/api/surveys/{sid}/questions/save-reusable", status_code=201)
    def save_reusable(
        sid: str,
        body: S.InstanceOperation,
        database=Depends(db),
        user=Depends(current_user),
    ):
        return question_instances.operation(database, user, sid, body, "save-question")
