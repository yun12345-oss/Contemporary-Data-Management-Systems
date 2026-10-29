from copy import deepcopy
import pytest
from app.domain.questions import validate_answer, REGISTRY, Number
from app.domain.rules import evaluate, check_definition, matches
from app.errors import BusinessError


@pytest.mark.parametrize(
    "value,valid",
    [
        (0, True),
        (120, True),
        (-1, False),
        (121, False),
        (18.5, False),
        (True, False),
        ("18", False),
        (None, False),
    ],
)
def test_number_bounds(definition, value, valid):
    q = definition["questions"][2]
    if valid:
        assert validate_answer(q, value) == value
    else:
        with pytest.raises(BusinessError):
            validate_answer(q, value)


@pytest.mark.parametrize(
    "value,valid",
    [
        (["a", "b"], True),
        (["a"], False),
        (["a", "b", "c"], False),
        (["a", "a"], False),
        (["a", "bad"], False),
    ],
)
def test_multiple(definition, value, valid):
    q = definition["questions"][1]
    if valid:
        assert validate_answer(q, value) == value
    else:
        with pytest.raises(BusinessError):
            validate_answer(q, value)


def test_routing_discards_skipped(definition):
    clean, path = evaluate(definition, {"q1": "worker", "q2": ["a", "b"], "q3": 18})
    assert path == ["q1", "q3", "q4"] and "q2" not in clean


def test_routing_requires_visited(definition):
    with pytest.raises(BusinessError) as exc:
        evaluate(definition, {"q1": "student", "q3": 18})
    assert "q2" in exc.value.details


@pytest.mark.parametrize(
    "op,value,answer,expected",
    [
        ("eq", 2, 2, True),
        ("ne", 2, 3, True),
        ("gt", 2, 2, False),
        ("gte", 2, 2, True),
        ("lt", 2, 1, True),
        ("lte", 2, 2, True),
        ("between", [2, 4], 4, True),
        ("contains_any", ["a", "b"], ["b"], True),
        ("contains_all", ["a", "b"], ["b"], False),
        ("set_equals", ["a", "b"], ["b", "a"], True),
        ("ne", 2, None, False),
    ],
)
def test_operators(op, value, answer, expected):
    assert (
        matches({"question_id": "x", "operator": op, "value": value}, {"x": answer})
        is expected
    )


def test_combination(definition):
    c = {
        "all": [
            {"question_id": "q1", "operator": "eq", "value": "student"},
            {
                "any": [
                    {"question_id": "q3", "operator": "gte", "value": 18},
                    {"question_id": "q3", "operator": "lt", "value": 0},
                ]
            },
        ]
    }
    assert matches(c, {"q1": "student", "q3": 18})
    assert not matches(c, {"q1": "student", "q3": 17})


@pytest.mark.parametrize("target", ["q1", "missing", 42])
def test_invalid_targets(definition, target):
    definition["questions"][0]["routing"]["rules"][0]["target"] = target
    with pytest.raises(BusinessError):
        check_definition(definition)


def test_future_reference(definition):
    definition["questions"][0]["routing"]["rules"][0]["condition"] = {
        "question_id": "q3",
        "operator": "gt",
        "value": 18,
    }
    with pytest.raises(BusinessError):
        check_definition(definition)


def test_duplicate_ids(definition):
    definition["questions"][1]["id"] = "q1"
    with pytest.raises(BusinessError):
        check_definition(definition)


def test_unknown_question(definition):
    with pytest.raises(BusinessError):
        evaluate(definition, {"hacked": 1})


def test_optional_text(definition):
    assert validate_answer(definition["questions"][3], "   ") is None
    assert validate_answer(definition["questions"][3], "  你好  ") == "你好"
    with pytest.raises(BusinessError):
        validate_answer(definition["questions"][3], "a")


def test_config_conflict(definition):
    definition["questions"][2]["validation"] = {"min": 100, "max": 1}
    with pytest.raises(BusinessError):
        check_definition(definition)


def test_extension_entry(definition):
    class Rating(Number):
        pass

    REGISTRY["rating"] = Rating()
    try:
        definition["questions"][2]["type"] = "rating"
        assert validate_answer(definition["questions"][2], 5) == 5
        check_definition(definition)
    finally:
        REGISTRY.pop("rating")
