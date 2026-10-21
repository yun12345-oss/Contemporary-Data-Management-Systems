"""所有 JSON 数值使用同一安全边界，避免浮点转换溢出和 BSON 编码失败。"""

import math

NUMBER_LIMIT = 10**15


def safe_number(value):
    return (
        type(value) in (int, float)
        and -NUMBER_LIMIT <= value <= NUMBER_LIMIT
        and (type(value) is int or math.isfinite(value))
    )


def check_json_numbers(value, depth=0):
    if depth > 32:
        raise ValueError("请求数据嵌套过深")
    if type(value) in (int, float) and not safe_number(value):
        raise ValueError("数值必须有限，且绝对值不超过 10¹⁵")
    if isinstance(value, dict):
        for item in value.values():
            check_json_numbers(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            check_json_numbers(item, depth + 1)
