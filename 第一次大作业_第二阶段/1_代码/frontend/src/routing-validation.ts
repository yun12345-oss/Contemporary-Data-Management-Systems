import type { Condition, Question } from "./types";
type ObjectValue = Record<string, unknown>;
export const operators: Record<string, { id: string; name: string }[]> = {
  single_choice: [
    { id: "eq", name: "等于" },
    { id: "ne", name: "不等于" },
  ],
  multiple_choice: [
    { id: "contains_any", name: "包含任一" },
    { id: "contains_all", name: "包含全部" },
    { id: "set_equals", name: "完全相同" },
  ],
  number: [
    { id: "eq", name: "等于" },
    { id: "ne", name: "不等于" },
    { id: "gt", name: "大于" },
    { id: "gte", name: "大于等于" },
    { id: "lt", name: "小于" },
    { id: "lte", name: "小于等于" },
    { id: "between", name: "介于（包含边界）" },
  ],
};
function check(ok: unknown, path: string, message: string): asserts ok {
  if (!ok) throw new Error(`${path}：${message}`);
}
function object(value: unknown, path: string): asserts value is ObjectValue {
  check(
    value !== null && typeof value === "object" && !Array.isArray(value),
    path,
    "必须是对象",
  );
}
function keys(value: ObjectValue, expected: string[], path: string) {
  check(
    Object.keys(value).length === expected.length &&
      expected.every((k) => Object.hasOwn(value, k)),
    path,
    `需要且仅允许字段 ${expected.join("、")}`,
  );
}
function safeNumber(value: unknown): value is number {
  return (
    typeof value === "number" &&
    Number.isFinite(value) &&
    Math.abs(value) <= 1e15
  );
}

/** 渲染安全边界：允许数字输入暂时为空，但不允许缺失容器、条件或数组。 */
export function assertRoutingShape(
  value: unknown,
): asserts value is Question["routing"] {
  object(value, "跳转配置");
  keys(value, ["rules", "default_target"], "跳转配置");
  check(
    Array.isArray(value.rules) && value.rules.length <= 20,
    "rules",
    "需要数组，最多20条",
  );
  check(
    value.default_target === null || typeof value.default_target === "string",
    "default_target",
    "必须是题目ID或null",
  );
  let nodes = 0;
  function shape(c: unknown, path: string, depth = 0) {
    check(depth <= 5 && ++nodes <= 2000, path, "条件过深或节点过多");
    object(c, path);
    if (Object.hasOwn(c, "all") || Object.hasOwn(c, "any")) {
      const key = Object.hasOwn(c, "all") ? "all" : "any";
      keys(c, [key], path);
      const children = c[key];
      check(
        Array.isArray(children) &&
          children.length >= 1 &&
          children.length <= 20,
        path,
        "组合条件需要1～20项",
      );
      children.forEach((child, i) =>
        shape(child, `${path}.${key}[${i}]`, depth + 1),
      );
      return;
    }
    keys(c, ["question_id", "operator", "value"], path);
    check(
      typeof c.question_id === "string" && typeof c.operator === "string",
      path,
      "来源题目与运算符必须是字符串",
    );
    if (c.operator === "between")
      check(
        Array.isArray(c.value) && c.value.length === 2,
        path,
        "区间值必须是两个元素的数组",
      );
    if (["contains_any", "contains_all", "set_equals"].includes(c.operator))
      check(Array.isArray(c.value), path, "多选条件值必须是数组");
  }
  value.rules.forEach((rule, i) => {
    const path = `第${i + 1}条规则`;
    object(rule, path);
    keys(rule, ["condition", "target"], path);
    check(typeof rule.target === "string", path, "目标必须是字符串");
    shape(rule.condition, `${path}.condition`);
  });
}

export function validateRouting(
  value: unknown,
  questions: Question[],
  index: number,
): asserts value is Question["routing"] {
  assertRoutingShape(value);
  check(index >= 0 && index < questions.length, "跳转配置", "当前题目不存在");
  const positions = new Map(questions.map((q, i) => [q.id, i]));
  check(positions.size === questions.length, "问卷", "题目ID重复");
  function target(t: string | null, path: string, nullable = false) {
    check(
      (nullable && t === null) ||
        (typeof t === "string" &&
          (t === "END" || (positions.has(t) && positions.get(t)! > index))),
      path,
      "目标只能是后续题目或 END",
    );
  }
  function condition(c: Condition, path: string) {
    if (c.all) {
      c.all.forEach((x, i) => condition(x, `${path}.all[${i}]`));
      return;
    }
    if (c.any) {
      c.any.forEach((x, i) => condition(x, `${path}.any[${i}]`));
      return;
    }
    const position = positions.get(c.question_id!);
    check(
      position !== undefined && position <= index,
      path,
      "只能引用当前或之前存在的题目",
    );
    const q = questions[position];
    check(
      operators[q.type]?.some((o) => o.id === c.operator),
      path,
      "运算符与题型不匹配",
    );
    const ids = new Set(q.options.map((o) => o.id));
    if (q.type === "single_choice")
      check(
        typeof c.value === "string" && ids.has(c.value),
        path,
        "引用了不存在的选项",
      );
    else if (q.type === "multiple_choice")
      check(
        Array.isArray(c.value) &&
          c.value.length > 0 &&
          new Set(c.value).size === c.value.length &&
          c.value.every((x: unknown) => typeof x === "string" && ids.has(x)),
        path,
        "需要非空、无重复且存在的选项数组",
      );
    else {
      const values = c.operator === "between" ? c.value : [c.value];
      check(
        Array.isArray(values) && values.every(safeNumber),
        path,
        "比较值必须有限且绝对值不超过10¹⁵",
      );
      check(
        c.operator !== "between" || values[0] <= values[1],
        path,
        "区间下界不能大于上界",
      );
    }
  }
  value.rules.forEach((rule, i) => {
    condition(rule.condition, `第${i + 1}条规则.condition`);
    target(rule.target, `第${i + 1}条规则.target`);
  });
  target(value.default_target, "default_target", true);
}
export function parseRouting(
  text: string,
  questions: Question[],
  index: number,
): Question["routing"] {
  check(text.length <= 1_000_000, "跳转配置", "内容过大");
  const value: unknown = JSON.parse(text);
  validateRouting(value, questions, index);
  return value;
}
