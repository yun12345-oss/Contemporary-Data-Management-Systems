import type { Definition, Question } from "./types";
import { matches, validate } from "./rules";
import { trimText } from "./text.ts";

export function answerValue(q: Question, raw: any): any {
  if (q.type !== "number" || typeof raw !== "string") return raw;
  const text = trimText(raw);
  if (!text) return null;
  return /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(text)
    ? Number(text)
    : raw;
}

export function draftPath(d: Definition, raw: Record<string, any>): Question[] {
  const result: Question[] = [],
    effective: Record<string, any> = {};
  let i = 0;
  while (
    i >= 0 &&
    i < d.questions.length &&
    result.length < d.questions.length
  ) {
    const q = d.questions[i];
    result.push(q);
    const value = answerValue(q, raw[q.id]);
    if (validate(q, value)) break;
    effective[q.id] = typeof value === "string" ? trimText(value) : value;
    const target =
      q.routing.rules.find((r) => matches(r.condition, effective))?.target ??
      q.routing.default_target;
    if (target === "END") break;
    i = target ? d.questions.findIndex((x) => x.id === target) : i + 1;
  }
  return result;
}

export function pruneSkipped(d: Definition, raw: Record<string, any>) {
  const path = draftPath(d, raw);
  const positions = new Map(d.questions.map((q, i) => [q.id, i]));
  for (let i = 1; i < path.length; i++) {
    const a = positions.get(path[i - 1].id)!,
      b = positions.get(path[i].id)!;
    for (let j = a + 1; j < b; j++) delete raw[d.questions[j].id];
  }
  const last = path.at(-1);
  if (last && !validate(last, answerValue(last, raw[last.id]))) {
    // 若有效路径提前结束，末题以后的内容确定失效。
    const lastIndex = positions.get(last.id)!;
    for (let j = lastIndex + 1; j < d.questions.length; j++)
      delete raw[d.questions[j].id];
  }
}
