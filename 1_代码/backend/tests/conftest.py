import os
from copy import deepcopy
from uuid import uuid4
import pytest
from pymongo import MongoClient
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture(scope="session")
def database():
    uri = os.getenv("TEST_MONGO_URI", "mongodb://127.0.0.1:27019/?replicaSet=survey-rs")
    client = MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=5000)
    # 永远只删除此次测试自行生成的数据库。
    name = "survey_lab_test_" + uuid4().hex
    db = client[name]
    client.admin.command("ping")
    yield db
    assert name.startswith("survey_lab_test_")
    client.drop_database(name)
    client.close()


@pytest.fixture
def app(database):
    return create_app(database, "test-secret-for-survey-lab-32-characters")


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        name = "user_" + uuid4().hex[:12]
        assert (
            client.post(
                "/api/auth/register",
                json={"username": name, "password": "TestPass123!"},
            ).status_code
            == 201
        )
        yield client


@pytest.fixture
def definition():
    return {
        "title": "测试问卷",
        "description": "覆盖全部题型",
        "allow_anonymous": True,
        "allow_repeat": False,
        "questions": [
            {
                "id": "q1",
                "type": "single_choice",
                "title": "你的身份",
                "required": True,
                "options": [
                    {"id": "student", "label": "学生"},
                    {"id": "worker", "label": "工作"},
                ],
                "validation": {},
                "routing": {
                    "rules": [
                        {
                            "condition": {
                                "question_id": "q1",
                                "operator": "eq",
                                "value": "worker",
                            },
                            "target": "q3",
                        }
                    ],
                    "default_target": None,
                },
            },
            {
                "id": "q2",
                "type": "multiple_choice",
                "title": "喜欢的课程",
                "required": True,
                "options": [
                    {"id": "a", "label": "数据库"},
                    {"id": "b", "label": "网络"},
                    {"id": "c", "label": "算法"},
                ],
                "validation": {"min_choices": 2, "max_choices": 2},
                "routing": {"rules": [], "default_target": None},
            },
            {
                "id": "q3",
                "type": "number",
                "title": "年龄",
                "required": True,
                "options": [],
                "validation": {"min": 0, "max": 120, "integer_only": True},
                "routing": {"rules": [], "default_target": None},
            },
            {
                "id": "q4",
                "type": "text",
                "title": "建议",
                "required": False,
                "options": [],
                "validation": {"min_length": 2, "max_length": 20},
                "routing": {"rules": [], "default_target": "END"},
            },
        ],
    }


def publish_survey(client, definition):
    r = client.post("/api/surveys", json={"title": definition["title"]})
    assert r.status_code == 201, r.text
    survey = r.json()
    r = client.put(
        f"/api/surveys/{survey['_id']}/draft",
        json={"revision": survey["revision"], "draft": definition},
    )
    assert r.status_code == 200, r.text
    survey = r.json()
    r = client.post(
        f"/api/surveys/{survey['_id']}/publish", json={"revision": survey["revision"]}
    )
    assert r.status_code == 200, r.text
    return client.get(f"/api/surveys/{survey['_id']}").json()


@pytest.fixture
def published(client, definition):
    return publish_survey(client, definition)


def start(client, survey, anonymous=False):
    r = client.post(
        f"/api/public/{survey['share_code']}/start", json={"anonymous": anonymous}
    )
    assert r.status_code == 200, r.text
    return r.json()["token"]
