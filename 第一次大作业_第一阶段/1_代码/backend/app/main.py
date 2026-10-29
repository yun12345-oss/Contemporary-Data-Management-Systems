from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import logging
from fastapi import FastAPI, Request, Response, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pymongo.errors import DuplicateKeyError, PyMongoError, WriteError
from pymongo import ReturnDocument
from app.config import settings, ROOT
from app.database import connect, initialize
from app.errors import BusinessError, require
from app.schemas import (
    Credentials,
    CreateSurvey,
    SaveDraft,
    Publish,
    StatusChange,
    StartAttempt,
    Submit,
    SaveAttempt,
    AttemptRevision,
)
from app.security import Security, passwords, new_session, digest, now, uid
from app.services import surveys, participation, statistics, attempts


def create_app(database=None, secret=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.security = Security(secret or settings.secret)
        if database is None:
            client = connect()
            hello = client.admin.command("hello")
            require(
                bool(hello.get("setName")),
                "MongoDB 必须以副本集运行，请使用项目启动脚本",
                500,
            )
            app.state.db = client[settings.database]
        else:
            client = None
            app.state.db = database
        initialize(app.state.db)
        yield
        if client:
            client.close()

    app = FastAPI(
        title="问序 Survey Lab",
        version="1.1.0",
        description="MongoDB 问卷系统第一阶段 API",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        # 同源 Cookie 会话；拒绝浏览器跨站写请求，不开放任意跨域。
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and origin not in settings.origins:
                return JSONResponse({"error": "不允许跨站操作"}, status_code=403)
            length = request.headers.get("content-length")
            if length and int(length) > 1_000_000:
                return JSONResponse({"error": "请求内容过大"}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(BusinessError)
    async def business_error(request, exc):
        return JSONResponse(
            {"error": exc.message, "details": exc.details}, status_code=exc.status
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(
            {
                "error": "请求字段格式不正确："
                + exc.errors()[0]["msg"].removeprefix("Value error, "),
                "details": [
                    {"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                    for e in exc.errors()
                ],
            },
            status_code=422,
        )

    @app.exception_handler(DuplicateKeyError)
    async def duplicate(request, exc):
        return JSONResponse(
            {"error": "记录已存在或操作重复，请刷新后重试"}, status_code=409
        )

    @app.exception_handler(OverflowError)
    async def numeric_overflow(request, exc):
        logging.warning("Rejected numeric overflow on %s", request.url.path)
        return JSONResponse({"error": "数值超出可存储范围"}, status_code=422)

    @app.exception_handler(PyMongoError)
    async def storage_error(request, exc):
        logging.exception("MongoDB operation failed")
        return JSONResponse({"error": "数据库暂时不可用，请稍后重试"}, status_code=503)

    @app.exception_handler(WriteError)
    async def document_error(request, exc):
        if exc.code == 121:
            return JSONResponse(
                {"error": "数据结构不符合数据库约束，请检查输入"}, status_code=422
            )
        logging.exception("MongoDB write failed")
        return JSONResponse({"error": "数据库写入失败，请稍后重试"}, status_code=503)

    def db(request: Request):
        return request.app.state.db

    def security(request: Request):
        return request.app.state.security

    def current_user(request: Request, database=Depends(db)):
        token = request.cookies.get("survey_session", "")
        session = database.sessions.find_one(
            {"token_hash": digest(token), "expires_at": {"$gt": now()}}
        )
        require(session is not None, "请先登录", 401)
        user = database.users.find_one({"_id": session["user_id"]})
        require(user is not None, "用户不存在", 401)
        return user

    def safe_user(user):
        return {"id": user["_id"], "username": user["username"]}

    @app.get("/api/health")
    def health(database=Depends(db)):
        database.command("ping")
        return {"status": "ok", "version": "1.1.0"}

    @app.post("/api/auth/register", status_code=201)
    def register(body: Credentials, response: Response, database=Depends(db)):
        user = {
            "_id": uid(),
            "username": body.username,
            "username_key": body.username.casefold(),
            "password_hash": passwords.hash(body.password),
            "created_at": now(),
            "schema_version": 1,
        }
        database.users.insert_one(user)
        response.set_cookie(
            "survey_session",
            new_session(database, user["_id"]),
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
            max_age=604800,
        )
        return safe_user(user)

    @app.post("/api/auth/login")
    def login(body: Credentials, response: Response, database=Depends(db)):
        user = database.users.find_one({"username_key": body.username.casefold()})
        require(
            user is not None and passwords.verify(body.password, user["password_hash"]),
            "用户名或密码错误",
            401,
        )
        response.set_cookie(
            "survey_session",
            new_session(database, user["_id"]),
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
            max_age=604800,
        )
        return safe_user(user)

    @app.post("/api/auth/logout")
    def logout(request: Request, response: Response, database=Depends(db)):
        database.sessions.delete_one(
            {"token_hash": digest(request.cookies.get("survey_session", ""))}
        )
        response.delete_cookie("survey_session")
        return {"ok": True}

    @app.get("/api/auth/me")
    def me(user=Depends(current_user)):
        return safe_user(user)

    @app.get("/api/surveys")
    def list_surveys(
        page: int = Query(1, ge=1), database=Depends(db), user=Depends(current_user)
    ):
        query = {"owner_id": user["_id"]}
        docs = list(
            database.surveys.find(query)
            .sort("created_at", -1)
            .skip((page - 1) * 20)
            .limit(20)
        )
        # 用一个聚合查询获取当前页的提交总数，避免逐条查询。
        counts = {
            r["_id"]: r["n"]
            for r in database.responses.aggregate(
                [
                    {"$match": {"survey_id": {"$in": [d["_id"] for d in docs]}}},
                    {"$group": {"_id": "$survey_id", "n": {"$sum": 1}}},
                ]
            )
        }
        for doc in docs:
            doc["response_count"] = counts.get(doc["_id"], 0)
        return {
            "items": docs,
            "total": database.surveys.count_documents(query),
            "page": page,
        }

    @app.post("/api/surveys", status_code=201)
    def create(body: CreateSurvey, database=Depends(db), user=Depends(current_user)):
        return surveys.create(database, user, body.title)

    @app.get("/api/surveys/{sid}")
    def get_survey(sid: str, database=Depends(db), user=Depends(current_user)):
        return surveys.owned(database, sid, user)

    @app.put("/api/surveys/{sid}/draft")
    def save(
        sid: str, body: SaveDraft, database=Depends(db), user=Depends(current_user)
    ):
        return surveys.save(database, sid, user, body)

    @app.post("/api/surveys/{sid}/publish")
    def publish(
        sid: str, body: Publish, database=Depends(db), user=Depends(current_user)
    ):
        return surveys.publish(database, sid, user, body)

    @app.patch("/api/surveys/{sid}/status")
    def status(
        sid: str, body: StatusChange, database=Depends(db), user=Depends(current_user)
    ):
        surveys.owned(database, sid, user)
        query = {"_id": sid, "owner_id": user["_id"]}
        if body.revision is not None:
            query["revision"] = body.revision
        updated = database.surveys.find_one_and_update(
            query,
            {
                "$set": {"status": body.status, "updated_at": now()},
                "$inc": {"revision": 1, "activity_seq": 1},
            },
            return_document=ReturnDocument.AFTER,
        )
        require(updated is not None, "问卷已被其他窗口修改，请先核对服务器状态", 409)
        return {"ok": True, "survey": surveys.survey_metadata(updated)}

    @app.get("/api/surveys/{sid}/versions")
    def versions(sid: str, database=Depends(db), user=Depends(current_user)):
        surveys.owned(database, sid, user)
        return list(
            database.survey_versions.find({"survey_id": sid}, {"definition": 0}).sort(
                "version", -1
            )
        )

    @app.get("/api/surveys/{sid}/versions/{version}")
    def version_detail(
        sid: str, version: int, database=Depends(db), user=Depends(current_user)
    ):
        return statistics.select_version(database, sid, user, version)

    @app.get("/api/public/{share}")
    def public_info(share: str, database=Depends(db), user=Depends(current_user)):
        survey = database.surveys.find_one({"share_code": share})
        surveys.available(survey)
        ver = database.survey_versions.find_one(
            {"survey_id": survey["_id"], "version": survey["current_version"]}
        )
        definition = ver["definition"]
        return {
            "title": definition["title"],
            "description": definition["description"],
            "allow_anonymous": definition["allow_anonymous"],
            "allow_repeat": definition["allow_repeat"],
            "question_count": len(definition["questions"]),
            "version": ver["version"],
            "deadline": survey.get("deadline"),
        }

    @app.post("/api/public/{share}/start")
    def start(
        share: str,
        body: StartAttempt,
        database=Depends(db),
        sec=Depends(security),
        user=Depends(current_user),
    ):
        return participation.start(database, sec, share, user, body.anonymous)

    @app.post("/api/responses")
    def submit(
        body: Submit,
        database=Depends(db),
        sec=Depends(security),
        user=Depends(current_user),
    ):
        return participation.submit(database, sec, user, body)

    @app.get("/api/public/{share}/attempt")
    def current_attempt(
        share: str,
        database=Depends(db),
        sec=Depends(security),
        user=Depends(current_user),
    ):
        return attempts.find_current(database, sec, user, share)

    @app.post("/api/public/{share}/attempt")
    def begin_attempt(
        share: str,
        body: StartAttempt,
        database=Depends(db),
        sec=Depends(security),
        user=Depends(current_user),
    ):
        return attempts.begin(database, sec, user, share, body.anonymous)

    @app.get("/api/attempts/{aid}")
    def read_attempt(
        aid: str,
        database=Depends(db),
        sec=Depends(security),
        user=Depends(current_user),
    ):
        return attempts.view(database, attempts.owned(database, sec, user, aid))

    @app.put("/api/attempts/{aid}")
    def save_attempt(
        aid: str,
        body: SaveAttempt,
        database=Depends(db),
        sec=Depends(security),
        user=Depends(current_user),
    ):
        return attempts.save(database, sec, user, aid, body)

    @app.post("/api/attempts/{aid}/abandon")
    def abandon_attempt(
        aid: str,
        body: AttemptRevision,
        database=Depends(db),
        sec=Depends(security),
        user=Depends(current_user),
    ):
        return attempts.abandon(database, sec, user, aid, body.revision)

    @app.post("/api/attempts/{aid}/submit")
    def submit_attempt(
        aid: str,
        body: AttemptRevision,
        database=Depends(db),
        sec=Depends(security),
        user=Depends(current_user),
    ):
        return attempts.submit(database, sec, user, aid, body.revision)

    @app.post("/api/evaluate")
    def evaluate_preview(
        body: Submit,
        database=Depends(db),
        sec=Depends(security),
        user=Depends(current_user),
    ):
        from app.domain.rules import evaluate

        attempt = sec.decode(body.token)
        require(attempt["user_id"] == user["_id"], "无权使用此凭证", 403)
        version = database.survey_versions.find_one({"_id": attempt["version_id"]})
        require(version is not None, "版本不存在", 404)
        clean, path = evaluate(version["definition"], body.answers)
        return {"answers": clean, "path": path}

    @app.get("/api/surveys/{sid}/statistics")
    def stats(
        sid: str,
        version: int | None = Query(None, ge=1),
        start: datetime | None = None,
        end: datetime | None = None,
        database=Depends(db),
        user=Depends(current_user),
    ):
        for value in (start, end):
            require(value is None or value.tzinfo is not None, "筛选时间必须包含时区")
        return statistics.aggregate(database, sid, user, version, start, end)

    @app.get("/api/surveys/{sid}/questions/{qid}/values")
    def values(
        sid: str,
        qid: str,
        version: int | None = Query(None, ge=1),
        page: int = Query(1, ge=1),
        start: datetime | None = None,
        end: datetime | None = None,
        database=Depends(db),
        user=Depends(current_user),
    ):
        for value in (start, end):
            require(value is None or value.tzinfo is not None, "筛选时间必须包含时区")
        return statistics.values(database, sid, user, qid, version, page, start, end)

    dist = ROOT / "frontend/dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            require(not path.startswith("api/"), "接口不存在", 404)
            return FileResponse(dist / "index.html")

    return app


app = create_app()
