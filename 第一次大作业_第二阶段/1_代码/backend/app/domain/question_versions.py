"""Reusable content is independent of survey-local required/routing settings."""

from copy import deepcopy

from app.domain.rules import check_definition
from app.errors import BusinessError

CONTENT_FIELDS = ("type", "title", "options", "validation")


def content_of(question):
    return {k: deepcopy(question[k]) for k in CONTENT_FIELDS}


def check_content(content):
    q = {
        **content,
        "id": "reusable",
        "required": True,
        "routing": {"rules": [], "default_target": None},
    }
    check_definition({"title": "题目版本", "questions": [q]})
    return content


def definition_issues(definition):
    """Drafts can be incomplete; publish always recomputes full validation."""
    try:
        check_definition(definition)
        return []
    except BusinessError as exc:
        return [exc.message]


def diff(before, after):
    return [
        {"field": k, "before": before[k], "after": after[k]}
        for k in CONTENT_FIELDS
        if before[k] != after[k]
    ]
