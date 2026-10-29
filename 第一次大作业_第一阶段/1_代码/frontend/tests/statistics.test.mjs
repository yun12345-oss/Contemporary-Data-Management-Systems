import test from "node:test";
import assert from "node:assert/strict";
import { optionCount, optionPercent } from "../src/statistics.ts";
test("重复作答的次数与去重人数分别选择分子和分母", () => {
  const question = { answered: 4, respondent_count: 2 };
  const option = { count: 3, respondent_count: 2 };
  assert.equal(optionCount(option, "responses"), 3);
  assert.equal(optionCount(option, "people"), 2);
  assert.equal(optionPercent(option, question, "responses"), 75);
  assert.equal(optionPercent(option, question, "people"), 100);
});
test("空数据百分比为零", () => {
  for (const basis of ["responses", "people"])
    assert.equal(
      optionPercent(
        { count: 0, respondent_count: 0 },
        { answered: 0, respondent_count: 0 },
        basis,
      ),
      0,
    );
});
test("允许单选多次改变答案形成重叠人数", () => {
  const question = { answered: 3, respondent_count: 1 };
  const a = { count: 2, respondent_count: 1 },
    b = { count: 1, respondent_count: 1 };
  assert.equal(
    optionPercent(a, question, "people") + optionPercent(b, question, "people"),
    200,
  );
});
