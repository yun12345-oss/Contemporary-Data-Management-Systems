"""Second-stage additive schemas; responses remain byte-for-byte unchanged."""

from copy import deepcopy


def extend(base):
    ident = {"bsonType": "string", "pattern": "^[A-Za-z0-9_-]{1,64}$"}
    text = lambda n=200: {"bsonType": "string", "minLength": 1, "maxLength": n}
    nullable_id = {"anyOf": [ident, {"bsonType": "null"}]}
    integer = {"bsonType": ["int", "long"], "minimum": 0, "maximum": 10**15}
    revision = {**integer, "minimum": 1}
    date = {"bsonType": "date"}
    boolean = {"bsonType": "bool"}
    ver = {"bsonType": ["int", "long"], "enum": [1]}

    def obj(props, required=None):
        return {
            "bsonType": "object",
            "properties": props,
            "required": list(props) if required is None else required,
            "additionalProperties": False,
        }

    source = obj(
        {
            "question_id": ident,
            "question_version_id": ident,
            "version": revision,
            "survey_id": ident,
            "instance_id": ident,
            "imported_by": ident,
            "imported_at": date,
            "grant_id": nullable_id,
        }
    )
    for name, field in [("surveys", "draft"), ("survey_versions", "definition")]:
        q = base[name]["properties"][field]["properties"]["questions"]["items"]
        q["properties"]["source"] = {"anyOf": [source, {"bsonType": "null"}]}
    q = deepcopy(
        base["surveys"]["properties"]["draft"]["properties"]["questions"]["items"]
    )
    content = obj(
        {k: q["properties"][k] for k in ["type", "title", "options", "validation"]}
    )
    content["properties"]["type"] = {
        "enum": ["single_choice", "multiple_choice", "text", "number"]
    }
    common = {"created_at": date, "schema_version": ver}
    base["questions"] = obj(
        {
            "_id": ident,
            "owner_id": ident,
            "title": text(500),
            "latest_version_id": ident,
            "version_seq": revision,
            "revision": revision,
            "archived": boolean,
            "activity_seq": integer,
            "updated_at": date,
            **common,
        }
    )
    base["question_versions"] = obj(
        {
            "_id": ident,
            "question_id": ident,
            "version": revision,
            "parent_version_id": nullable_id,
            "restored_from_version_id": nullable_id,
            "content": content,
            "change_note": {"bsonType": "string", "maxLength": 1000},
            "created_by": ident,
            **common,
        }
    )
    base["question_libraries"] = obj(
        {
            "_id": ident,
            "owner_id": ident,
            "name": text(),
            "description": {"bsonType": "string", "maxLength": 2000},
            "revision": revision,
            "updated_at": date,
            **common,
        }
    )
    base["question_library_items"] = obj(
        {
            "_id": ident,
            "library_id": ident,
            "question_id": ident,
            "question_version_id": ident,
            "position": {**integer, "maximum": 100000},
            **common,
        }
    )
    base["resource_grants"] = obj(
        {
            "_id": ident,
            "kind": {"enum": ["use", "aggregate"]},
            "question_version_id": ident,
            "survey_id": nullable_id,
            "grantor_id": ident,
            "grantee_id": ident,
            "active": boolean,
            "revision": revision,
            "activity_seq": integer,
            "updated_at": date,
            **common,
        }
    )
    base["resource_grants"]["oneOf"] = [
        {"properties": {"kind": {"enum": ["use"]}, "survey_id": {"bsonType": "null"}}},
        {"properties": {"kind": {"enum": ["aggregate"]}, "survey_id": ident}},
    ]
    return base
