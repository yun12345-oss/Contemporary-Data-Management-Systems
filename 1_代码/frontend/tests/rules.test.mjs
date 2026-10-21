import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { matches, pathOf, validate } from "../src/rules.ts";
const definition = JSON.parse(
  readFileSync(
    new URL("../../database/examples/survey_version.json", import.meta.url),
    "utf8",
  ),
).definition;

test("学生路径包含工具题，工作路径跳过工具题", () => {
  assert.deepEqual(
    pathOf(definition, { q_role: "student" }).map((q) => q.id),
    ["q_role", "q_tools", "q_hours", "q_feedback"],
  );
  assert.deepEqual(
    pathOf(definition, { q_role: "worker" }).map((q) => q.id),
    ["q_role", "q_hours", "q_feedback"],
  );
});
test("先前路径失效的答案不能参与后续条件", () => {
  const d = structuredClone(definition);
  d.questions[2].routing.rules = [
    {
      condition: {
        question_id: "q_tools",
        operator: "contains_any",
        value: ["mongo"],
      },
      target: "END",
    },
  ];
  assert.deepEqual(
    pathOf(d, { q_role: "worker", q_tools: ["mongo"], q_hours: 5 }).map(
      (q) => q.id,
    ),
    ["q_role", "q_hours", "q_feedback"],
  );
});
test("数字范围包含边界并拒绝非整数", () => {
  const q = definition.questions[2];
  assert.equal(validate(q, 0), "");
  assert.equal(validate(q, 40), "");
  assert.notEqual(validate(q, 41), "");
  assert.notEqual(validate(q, 1.5), "");
});
test("必答与可选空值保持区分", () => {
  assert.notEqual(validate(definition.questions[0], null), "");
  assert.equal(validate(definition.questions[3], "  "), "");
  assert.notEqual(validate(definition.questions[3], "a"), "");
});
test("多选数量约束", () => {
  const q = definition.questions[1];
  assert.notEqual(validate(q, ["mongo"]), "");
  assert.equal(validate(q, ["mongo", "python"]), "");
});
test("组合条件和区间边界", () => {
  const c = {
    all: [
      { question_id: "a", operator: "between", value: [18, 60] },
      {
        any: [
          { question_id: "b", operator: "eq", value: "x" },
          { question_id: "b", operator: "eq", value: "y" },
        ],
      },
    ],
  };
  assert.equal(matches(c, { a: 18, b: "x" }), true);
  assert.equal(matches(c, { a: 60, b: "y" }), true);
  assert.equal(matches(c, { a: 17, b: "x" }), false);
});
test("未回答的非等于条件也不满足", () => {
  assert.equal(
    matches({ question_id: "x", operator: "ne", value: "y" }, {}),
    false,
  );
});
test("Unicode 长度按码点计数", () => {
  const q = {
    ...definition.questions[3],
    validation: { min_length: 1, max_length: 1 },
  };
  assert.equal(validate(q, "😀"), "");
  assert.notEqual(validate(q, "😀😀"), "");
});
