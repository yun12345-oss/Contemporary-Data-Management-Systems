"""生成基本结构约束。业务级引用与可满足性仍由应用校验。"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def obj(properties, required=None, **extra):
    result = {"bsonType": "object", "properties": properties, **extra}
    keys = list(properties) if required is None else required
    if keys:
        result["required"] = keys
    return result


def string(max_length=200, min_length=1):
    return {"bsonType": "string", "minLength": min_length, "maxLength": max_length}


def array(items, max_items=100, **extra):
    return {"bsonType": "array", "items": items, "maxItems": max_items, **extra}


def build_base():
    id_field = {"bsonType": "string", "pattern": "^[A-Za-z0-9_-]{1,64}$"}
    integer = {"bsonType": ["int", "long"], "minimum": 0, "maximum": 10**15}
    number = {
        "bsonType": ["int", "long", "double"],
        "minimum": -(10**15),
        "maximum": 10**15,
    }
    boolean = {"bsonType": "bool"}
    date = {"bsonType": "date"}
    version = {"bsonType": ["int", "long"], "enum": [1]}
    option = obj({"id": id_field, "label": string(200)})
    validation = obj(
        {
            "min_choices": integer,
            "max_choices": integer,
            "min_length": integer,
            "max_length": integer,
            "min": number,
            "max": number,
            "integer_only": boolean,
        },
        required=[],
    )
    # 校验规则保留字段扩展空间；只约束内置字段，不绑定尚未定义的未来题型。
    condition = {"bsonType": "object", "minProperties": 1}
    target = {"bsonType": ["null", "string"]}
    rule = obj({"condition": condition, "target": string(64)})
    routing = obj({"rules": array(rule, 20), "default_target": target})
    question = obj(
        {
            "id": id_field,
            "type": string(40),
            "title": string(500),
            "required": boolean,
            "options": array(option),
            "validation": validation,
            "routing": routing,
        }
    )
    definition = obj(
        {
            "title": string(200),
            "description": string(5000, 0),
            "allow_anonymous": boolean,
            "allow_repeat": boolean,
            "questions": array(question),
        }
    )
    published_definition = {
        **definition,
        "properties": {
            **definition["properties"],
            "questions": array(question, minItems=1),
        },
    }
    answer_value = {
        "anyOf": [
            {"bsonType": "null"},
            string(10000),
            number,
            array(id_field, uniqueItems=True, minItems=1),
        ]
    }
    answer = obj(
        {"question_id": id_field, "value": answer_value}, additionalProperties=False
    )
    user = obj(
        {
            "_id": id_field,
            "username": string(40, 3),
            "username_key": string(200),
            "password_hash": string(1024),
            "created_at": date,
            "schema_version": version,
        }
    )
    session = obj(
        {
            "_id": id_field,
            "token_hash": {"bsonType": "string", "pattern": "^[a-f0-9]{64}$"},
            "user_id": id_field,
            "expires_at": date,
        }
    )
    survey = obj(
        {
            "_id": id_field,
            "owner_id": id_field,
            "share_code": id_field,
            "status": {"enum": ["draft", "published", "closed"]},
            "draft": definition,
            "deadline": {"bsonType": ["date", "null"]},
            "revision": {"bsonType": ["int", "long"], "minimum": 1},
            "current_version": integer,
            "created_at": date,
            "updated_at": date,
            "activity_seq": integer,
            "schema_version": version,
        }
    )
    survey_version = obj(
        {
            "_id": id_field,
            "survey_id": id_field,
            "version": {"bsonType": ["int", "long"], "minimum": 1},
            "definition": published_definition,
            "schema_version": version,
            "rule_engine_version": version,
            "published_at": date,
        }
    )
    response = obj(
        {
            "_id": id_field,
            "survey_id": id_field,
            "version_id": id_field,
            "version": {"bsonType": ["int", "long"], "minimum": 1},
            "attempt_id": id_field,
            "respondent_key": {"bsonType": "string", "pattern": "^[a-f0-9]{64}$"},
            "anonymous": boolean,
            "answers": array(answer, minItems=1),
            "path": array(id_field, minItems=1, uniqueItems=True),
            "submitted_at": date,
            "schema_version": version,
            "user_id": id_field,
        },
        required=[
            "_id",
            "survey_id",
            "version_id",
            "version",
            "attempt_id",
            "respondent_key",
            "anonymous",
            "answers",
            "path",
            "submitted_at",
            "schema_version",
        ],
    )
    response["oneOf"] = [
        {
            "properties": {"anonymous": {"enum": [True]}},
            "not": {"required": ["user_id"]},
        },
        {"properties": {"anonymous": {"enum": [False]}}, "required": ["user_id"]},
    ]
    return dict(
        users=user,
        sessions=session,
        surveys=survey,
        survey_versions=survey_version,
        responses=response,
        attempts=obj(
            {
                "_id": id_field,
                "survey_id": id_field,
                "version_id": id_field,
                "respondent_key": {"bsonType": "string", "pattern": "^[a-f0-9]{64}$"},
                "anonymous": boolean,
                "status": {
                    "bsonType": "string",
                    "enum": ["in_progress", "submitted", "abandoned"],
                },
                "raw_answers": {
                    "bsonType": "object",
                    "maxProperties": 100,
                    "additionalProperties": {
                        "anyOf": [
                            {"bsonType": "null"},
                            string(20000, 0),
                            number,
                            array(id_field),
                        ]
                    },
                },
                "current_question_id": id_field,
                "revision": {"bsonType": ["int", "long"], "minimum": 1},
                "created_at": date,
                "updated_at": date,
                "schema_version": version,
                "response_id": id_field,
            },
            required=[
                "_id",
                "survey_id",
                "version_id",
                "respondent_key",
                "anonymous",
                "status",
                "raw_answers",
                "current_question_id",
                "revision",
                "created_at",
                "updated_at",
                "schema_version",
            ],
        ),
    )


def build():
    try:
        from .phase2_validators import extend
    except ImportError:
        from phase2_validators import extend
    return extend(build_base())


if __name__ == "__main__":
    (ROOT / "collection_validators.json").write_text(
        json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
