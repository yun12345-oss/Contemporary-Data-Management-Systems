import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { parseRouting, assertRoutingShape } from "../src/routing-validation.ts";
const qs = JSON.parse(
  readFileSync(
    new URL("../../database/examples/survey_version.json", import.meta.url),
    "utf8",
  ),
).definition.questions;
test("规则缺少 condition 不允许应用", () =>
  assert.throws(
    () => parseRouting('{"rules":[{}],"default_target":null}', qs, 0),
    /第1条规则/,
  ));
test("结构、类型、引用、顺序与数值边界均检查", () => {
  const invalid = [
    null,
    [],
    { rules: [], default_target: null, extra: 1 },
    {
      rules: [
        {
          condition: { question_id: "q_hours", operator: "gt", value: 18 },
          target: "END",
        },
      ],
      default_target: null,
    },
    {
      rules: [
        {
          condition: {
            question_id: "q_role",
            operator: "eq",
            value: "missing",
          },
          target: "END",
        },
      ],
      default_target: null,
    },
    {
      rules: [
        {
          condition: { question_id: "q_role", operator: "eq", value: "worker" },
          target: "q_role",
        },
      ],
      default_target: null,
    },
  ];
  for (const value of invalid)
    assert.throws(() => parseRouting(JSON.stringify(value), qs, 0));
});
test("有效组合条件保留不改变", () => {
  const value = {
    rules: [
      {
        condition: {
          all: [
            { question_id: "q_role", operator: "eq", value: "worker" },
            { question_id: "q_hours", operator: "between", value: [0, 40] },
          ],
        },
        target: "END",
      },
    ],
    default_target: null,
  };
  assert.deepEqual(parseRouting(JSON.stringify(value), qs, 2), value);
});
test("区间与多选值结构损坏不会进入渲染", () => {
  for (const c of [
    { question_id: "q_hours", operator: "between", value: null },
    { question_id: "q_tools", operator: "contains_all", value: "mongo" },
  ])
    assert.throws(() =>
      assertRoutingShape({
        rules: [{ condition: c, target: "END" }],
        default_target: null,
      }),
    );
});
test("组合条件层数、空数组与超大数值不通过", () => {
  let c = { question_id: "q_hours", operator: "gt", value: 1 };
  for (let i = 0; i < 7; i++) c = { all: [c] };
  for (const condition of [
    c,
    { all: [] },
    { all: [], any: [] },
    { question_id: "q_hours", operator: "between", value: [20, 10] },
    { question_id: "q_hours", operator: "gt", value: 1e20 },
  ])
    assert.throws(() =>
      parseRouting(
        JSON.stringify({
          rules: [{ condition, target: "END" }],
          default_target: null,
        }),
        qs,
        2,
      ),
    );
});
