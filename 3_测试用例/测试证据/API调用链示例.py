import json
from uuid import uuid4
import httpx

definition = json.loads(r'''{
  "title": "课程学习与实践调查",
  "description": "用于说明文档结构与路径的脱敏示例",
  "allow_anonymous": true,
  "allow_repeat": true,
  "questions": [
    {
      "id": "q_role",
      "type": "single_choice",
      "title": "你的身份",
      "required": true,
      "options": [
        {
          "id": "student",
          "label": "学生"
        },
        {
          "id": "worker",
          "label": "已工作"
        }
      ],
      "validation": {},
      "routing": {
        "rules": [
          {
            "condition": {
              "question_id": "q_role",
              "operator": "eq",
              "value": "worker"
            },
            "target": "q_age"
          }
        ],
        "default_target": null
      }
    },
    {
      "id": "q_tools",
      "type": "multiple_choice",
      "title": "使用过哪些工具",
      "required": true,
      "options": [
        {
          "id": "mongo",
          "label": "MongoDB"
        },
        {
          "id": "python",
          "label": "Python"
        },
        {
          "id": "java",
          "label": "Java"
        }
      ],
      "validation": {
        "min_choices": 2,
        "max_choices": 2
      },
      "routing": {
        "rules": [
          {
            "condition": {
              "question_id": "q_tools",
              "operator": "contains_all",
              "value": [
                "mongo",
                "python"
              ]
            },
            "target": "q_feedback"
          }
        ],
        "default_target": null
      }
    },
    {
      "id": "q_age",
      "type": "number",
      "title": "年龄",
      "required": true,
      "options": [],
      "validation": {
        "min": 0,
        "max": 120,
        "integer_only": true
      },
      "routing": {
        "rules": [
          {
            "condition": {
              "question_id": "q_age",
              "operator": "between",
              "value": [
                60,
                120
              ]
            },
            "target": "END"
          }
        ],
        "default_target": null
      }
    },
    {
      "id": "q_feedback",
      "type": "text",
      "title": "建议",
      "required": false,
      "options": [],
      "validation": {
        "min_length": 2,
        "max_length": 100
      },
      "routing": {
        "rules": [],
        "default_target": "END"
      }
    }
  ]
}''')
password = "ExamplePass123!"
owner = "owner_" + uuid4().hex[:10]
filler = "filler_" + uuid4().hex[:10]
def result(response):
    response.raise_for_status()
    return response.json()

with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as c:
    result(c.get("/api/health"))
    result(c.post("/api/auth/register", json={"username":owner,"password":password}))
    survey = result(c.post("/api/surveys", json={"title":definition["title"]}))
    sid, share = survey["_id"], survey["share_code"]
    survey = result(c.put(f"/api/surveys/{sid}/draft", json={"revision":survey["revision"],"draft":definition}))
    published = result(c.post(f"/api/surveys/{sid}/publish", json={"revision":survey["revision"],"deadline":None}))
    result(c.post("/api/auth/logout"))
    result(c.post("/api/auth/register", json={"username":filler,"password":password}))
    assert result(c.get(f"/api/public/{share}/attempt")) is None
    attempt = result(c.post(f"/api/public/{share}/attempt", json={"anonymous":True}))
    aid = attempt["_id"]
    attempt = result(c.put(f"/api/attempts/{aid}", json={"revision":attempt["revision"],"answers":{"q_role":"worker","q_age":"-"},"current_question_id":"q_age"}))
    restored = result(c.get(f"/api/public/{share}/attempt"))
    assert restored["_id"] == aid and restored["answers"]["q_age"] == "-"
    attempt = result(c.put(f"/api/attempts/{aid}", json={"revision":restored["revision"],"answers":{"q_role":"worker","q_age":"40","q_feedback":None},"current_question_id":"q_feedback"}))
    body = {"revision":attempt["revision"]}
    receipt = result(c.post(f"/api/attempts/{aid}/submit", json=body))
    assert result(c.post(f"/api/attempts/{aid}/submit", json=body)) == receipt
    result(c.post("/api/auth/logout"))
    result(c.post("/api/auth/login", json={"username":owner,"password":password}))
    stats = result(c.get(f"/api/surveys/{sid}/statistics", params={"version":published["version"]}))
    assert stats["total"] == stats["respondent_count"] == 1
    survey = result(c.get(f"/api/surveys/{sid}"))
    result(c.patch(f"/api/surveys/{sid}/status", json={"status":"closed","revision":survey["revision"]}))
    print({"survey_id":sid,"response_id":receipt["id"],"total":stats["total"]})
