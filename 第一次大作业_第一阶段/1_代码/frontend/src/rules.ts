import type { Condition, Definition, Question } from "./types";
import { textLength, trimText } from "./text.ts";
export function matches(c: Condition, answers: Record<string, any>): boolean {
  if (c.all) return c.all.every((x) => matches(x, answers));
  if (c.any) return c.any.some((x) => matches(x, answers));
  const a = answers[c.question_id!],
    b = c.value;
  if (
    a === undefined ||
    a === null ||
    a === "" ||
    (Array.isArray(a) && !a.length)
  )
    return false;
  switch (c.operator) {
    case "eq":
      return a === b;
    case "ne":
      return a !== b;
    case "gt":
      return a > b;
    case "gte":
      return a >= b;
    case "lt":
      return a < b;
    case "lte":
      return a <= b;
    case "between":
      return a >= b[0] && a <= b[1];
    case "contains_any":
      return b.some((x: string) => a.includes(x));
    case "contains_all":
      return b.every((x: string) => a.includes(x));
    case "set_equals":
      return a.length === b.length && b.every((x: string) => a.includes(x));
    default:
      return false;
  }
}
export function pathOf(
  d: Definition,
  answers: Record<string, any>,
): Question[] {
  const result: Question[] = [],
    seen = new Set<string>(),
    effective: Record<string, any> = {};
  let i = 0;
  while (i < d.questions.length) {
    const q = d.questions[i];
    if (seen.has(q.id)) break;
    seen.add(q.id);
    result.push(q);
    const raw = answers[q.id];
    effective[q.id] = typeof raw === "string" ? trimText(raw) : raw;
    const rule = q.routing.rules.find((r) => matches(r.condition, effective));
    const target = rule ? rule.target : q.routing.default_target;
    if (target === "END") break;
    i = target ? d.questions.findIndex((x) => x.id === target) : i + 1;
    if (i < 0) break;
  }
  return result;
}
export function validate(q: Question, value: any): string {
  const blank =
    value === undefined ||
    value === null ||
    value === "" ||
    (Array.isArray(value) && !value.length) ||
    (typeof value === "string" && !trimText(value));
  if (blank) return q.required ? "此题必须回答" : "";
  if (q.type === "single_choice" && !q.options.some((o) => o.id === value))
    return "请选择有效选项";
  if (
    q.type === "multiple_choice" &&
    (!Array.isArray(value) ||
      new Set(value).size !== value.length ||
      value.some((x) => !q.options.some((o) => o.id === x)))
  )
    return "请选择有效且不重复的选项";
  if (q.type === "text" && typeof value !== "string") return "请输入文本";
  const v = q.validation;
  if (
    q.type === "multiple_choice" &&
    (value.length < (v.min_choices ?? 0) ||
      value.length > (v.max_choices ?? q.options.length))
  )
    return "选择数量不符合要求";
  if (
    q.type === "text" &&
    (textLength(value) < (v.min_length ?? 0) ||
      textLength(value) > (v.max_length ?? 10000))
  )
    return "文本长度不符合要求";
  if (q.type === "number") {
    if (!Number.isFinite(value) || Math.abs(value) > 1e15)
      return "请输入有效数字";
    if (value < (v.min ?? -Infinity) || value > (v.max ?? Infinity))
      return "数字超出允许范围";
    if (v.integer_only && !Number.isInteger(value)) return "必须输入整数";
  }
  return "";
}
