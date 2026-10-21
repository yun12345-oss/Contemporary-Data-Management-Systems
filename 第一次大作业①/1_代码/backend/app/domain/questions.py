"""题型扩展入口：配置与答案校验使用普通数据，统计方法封装 MongoDB 聚合。"""

import math
from app.errors import require
from app.domain.numbers import safe_number, NUMBER_LIMIT
from app.aggregation import option_counts


class QuestionType:
    allowed_validation = set()
    operators = set()

    def check_config(self, q):
        require(
            set(q["validation"]) <= self.allowed_validation,
            f"{q['title']}：存在不支持的校验配置",
        )

    def validate(self, q, value):
        return value

    def summarize(self, db, base, q):
        return {}


class Single(QuestionType):
    operators = {"eq", "ne"}

    def summarize(self, db, base, q):
        return {"options": option_counts(db, base, q["options"])}

    def check_config(self, q):
        super().check_config(q)
        require(2 <= len(q["options"]) <= 100, "选择题至少需要两个选项")
        require(
            len({o["id"] for o in q["options"]}) == len(q["options"]),
            "选项 ID 不能重复",
        )

    def validate(self, q, value):
        require(
            isinstance(value, str) and value in {o["id"] for o in q["options"]},
            "请选择有效选项",
        )
        return value


class Multiple(Single):
    allowed_validation = {"min_choices", "max_choices"}
    operators = {"contains_any", "contains_all", "set_equals"}

    def summarize(self, db, base, q):
        return super().summarize(db, base + [{"$unwind": "$answers.value"}], q)

    def check_config(self, q):
        super().check_config(q)
        v = q["validation"]
        low, high = v.get("min_choices", 0), v.get("max_choices", len(q["options"]))
        require(
            type(low) is int
            and type(high) is int
            and 0 <= low <= high <= len(q["options"]),
            "多选数量限制不合法",
        )
        require(
            not q["required"] or max(1, low) <= high, "必答多选题必须允许至少选择一项"
        )

    def validate(self, q, value):
        require(
            isinstance(value, list) and all(isinstance(x, str) for x in value),
            "多选答案应为选项数组",
        )
        require(len(value) == len(set(value)), "选项不能重复")
        require(set(value) <= {o["id"] for o in q["options"]}, "包含无效选项")
        v = q["validation"]
        require(
            v.get("min_choices", 0)
            <= len(value)
            <= v.get("max_choices", len(q["options"])),
            "选择数量不符合要求",
        )
        return value


class Text(QuestionType):
    allowed_validation = {"min_length", "max_length"}

    def check_config(self, q):
        super().check_config(q)
        v = q["validation"]
        low, high = v.get("min_length", 0), v.get("max_length", 10000)
        require(
            type(low) is int and type(high) is int and 0 <= low <= high <= 10000,
            "文本长度限制不合法",
        )
        require(not q["options"], "填空题不能包含选项")
        require(
            not q["required"] or high >= max(1, low),
            "必答文本题必须允许输入至少一个字符",
        )

    def validate(self, q, value):
        require(isinstance(value, str), "请输入文本")
        value = value.strip()
        v = q["validation"]
        require(
            v.get("min_length", 0) <= len(value) <= v.get("max_length", 10000),
            "文本长度不符合要求",
        )
        return value


class Number(QuestionType):
    allowed_validation = {"min", "max", "integer_only"}
    operators = {"eq", "ne", "gt", "gte", "lt", "lte", "between"}

    def summarize(self, db, base, q):
        values = list(
            db.responses.aggregate(
                base
                + [
                    {
                        "$group": {
                            "_id": None,
                            "average": {"$avg": "$answers.value"},
                            "min": {"$min": "$answers.value"},
                            "max": {"$max": "$answers.value"},
                        }
                    },
                    {"$project": {"_id": 0}},
                ]
            )
        )
        return values[0] if values else {"average": None, "min": None, "max": None}

    def check_config(self, q):
        super().check_config(q)
        v = q["validation"]
        require(
            all(safe_number(v[k]) for k in ("min", "max") if k in v),
            "数字范围必须有限，且绝对值不超过 10¹⁵",
        )
        require(
            v.get("min", -math.inf) <= v.get("max", math.inf), "最小值不能超过最大值"
        )
        require(type(v.get("integer_only", False)) is bool, "整数限制必须是布尔值")
        low, high = v.get("min", -NUMBER_LIMIT), v.get("max", NUMBER_LIMIT)
        require(
            not (q["required"] and v.get("integer_only"))
            or math.ceil(low) <= math.floor(high),
            "必答整数题的范围内不存在合法整数",
        )
        require(not q["options"], "填空题不能包含选项")

    def validate(self, q, value):
        require(
            safe_number(value),
            "请输入有效数字（绝对值不超过 10¹⁵）",
        )
        v = q["validation"]
        require(
            v.get("min", -math.inf) <= value <= v.get("max", math.inf),
            "数字超出允许范围",
        )
        require(not v.get("integer_only") or float(value).is_integer(), "必须输入整数")
        return int(value) if v.get("integer_only") else value


REGISTRY = {
    "single_choice": Single(),
    "multiple_choice": Multiple(),
    "text": Text(),
    "number": Number(),
}


def handler(kind):
    require(kind in REGISTRY, f"不支持的题型：{kind}")
    return REGISTRY[kind]


def empty(value):
    return (
        value is None
        or value == ""
        or value == []
        or isinstance(value, str)
        and not value.strip()
    )


def validate_answer(q, value):
    if empty(value):
        require(not q["required"], "此题必须回答")
        return None
    return handler(q["type"]).validate(q, value)
