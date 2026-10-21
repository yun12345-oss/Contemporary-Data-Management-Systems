"""有限条件语言。禁止 eval；所有引用在发布前检查。"""

import operator
from app.errors import require, BusinessError
from app.domain.questions import handler, validate_answer
from app.domain.numbers import safe_number

COMPARATORS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
}


def check_condition(c, questions, position, depth=0):
    require(depth <= 5 and isinstance(c, dict), "条件嵌套过深或格式错误")
    if "all" in c or "any" in c:
        key = "all" if "all" in c else "any"
        require(
            set(c) == {key} and isinstance(c[key], list) and 1 <= len(c[key]) <= 20,
            "组合条件需要 1～20 个子条件",
        )
        for child in c[key]:
            check_condition(child, questions, position, depth + 1)
        return
    require(set(c) == {"question_id", "operator", "value"}, "条件字段不完整")
    ref = c["question_id"]
    require(isinstance(ref, str) and ref in questions, "条件引用了不存在的题目")
    idx, q = questions[ref]
    require(idx <= position, "条件不能引用尚未回答的后续题目")
    op, value = c["operator"], c["value"]
    require(
        isinstance(op, str) and op in handler(q["type"]).operators,
        "条件运算符与题型不匹配",
    )
    if q["type"] == "single_choice":
        require(
            isinstance(value, str) and value in {o["id"] for o in q["options"]},
            "条件引用了不存在的选项",
        )
    elif q["type"] == "multiple_choice":
        require(
            isinstance(value, list)
            and len(value) > 0
            and all(isinstance(x, str) for x in value),
            "多选条件需要选项数组",
        )
        require(
            len(set(value)) == len(value)
            and set(value) <= {o["id"] for o in q["options"]},
            "多选条件选项无效",
        )
    else:
        values = value if op == "between" else [value]
        require(
            isinstance(values, list) and len(values) == (2 if op == "between" else 1),
            "数字条件格式不正确",
        )
        require(
            all(safe_number(x) for x in values),
            "条件值必须有限，且绝对值不超过 10¹⁵",
        )
        require(op != "between" or values[0] <= values[1], "区间下界不能超过上界")


def matches(c, answers):
    if "all" in c:
        return all(matches(x, answers) for x in c["all"])
    if "any" in c:
        return any(matches(x, answers) for x in c["any"])
    current = answers.get(c["question_id"])
    if current is None:
        return False
    op, value = c["operator"], c["value"]
    if op in COMPARATORS:
        return COMPARATORS[op](current, value)
    if op == "contains_any":
        return bool(set(current) & set(value))
    if op == "contains_all":
        return set(value) <= set(current)
    if op == "set_equals":
        return set(current) == set(value)
    if op == "between":
        return value[0] <= current <= value[1]
    raise BusinessError("未知条件运算符")


def check_definition(definition):
    qs = definition["questions"]
    require(1 <= len(qs) <= 100, "发布需要 1～100 道题目")
    require(len({q["id"] for q in qs}) == len(qs), "题目 ID 不能重复")
    require(
        all(q["id"] != "END" and q["title"].strip() for q in qs),
        "题目标题不能为空，题目 ID 不能为 END",
    )
    require(bool(definition["title"].strip()), "问卷标题不能为空")
    questions = {q["id"]: (i, q) for i, q in enumerate(qs)}
    for i, q in enumerate(qs):
        handler(q["type"]).check_config(q)
        require(all(o["label"].strip() for o in q["options"]), "选项文字不能为空")
        routing = q["routing"]
        require(set(routing) <= {"rules", "default_target"}, "不支持的跳转配置字段")
        rules = routing.get("rules", [])
        require(isinstance(rules, list) and len(rules) <= 20, "每题最多 20 条跳转规则")
        targets = [routing.get("default_target")]
        for rule in rules:
            require(
                isinstance(rule, dict) and set(rule) == {"condition", "target"},
                "跳转规则字段错误",
            )
            check_condition(rule["condition"], questions, i)
            targets.append(rule["target"])
        for target in targets:
            require(target is None or isinstance(target, str), "跳转目标格式错误")
            require(
                target is None
                or target == "END"
                or target in questions
                and questions[target][0] > i,
                "跳转只能指向后续题目或 END",
            )


def route_target(q, answers):
    for rule in q["routing"].get("rules", []):
        if matches(rule["condition"], answers):
            return rule["target"]
    return q["routing"].get("default_target")


def evaluate(definition, raw):
    """只接纳真实路径上的答案；未到达题目的合法旧答案被排除。"""
    qs = definition["questions"]
    positions = {q["id"]: i for i, q in enumerate(qs)}
    require(set(raw) <= set(positions), "提交包含未知题目")
    clean, path, issues = {}, [], {}
    i = 0
    while i < len(qs):
        q = qs[i]
        path.append(q["id"])
        try:
            clean[q["id"]] = validate_answer(q, raw.get(q["id"]))
        except BusinessError as exc:
            issues[q["id"]] = exc.message
            clean[q["id"]] = None
        target = route_target(q, clean)
        if target == "END":
            break
        i = positions[target] if target else i + 1
    if issues:
        raise BusinessError("请检查填写内容", details=issues)
    return clean, path
