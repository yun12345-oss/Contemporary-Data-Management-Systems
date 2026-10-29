<script setup lang="ts">
import type { Question, Condition } from "../types";
import { computed } from "vue";
import { operators, assertRoutingShape } from "../routing-validation";
const props = defineProps<{
  question: Question;
  questions: Question[];
  index: number;
}>();
const structuralProblem = computed(() => {
  try {
    assertRoutingShape(props.question.routing);
    return "";
  } catch (e: any) {
    return e.message;
  }
});
const safeRules = computed(() =>
  structuralProblem.value ? [] : props.question.routing.rules,
);
function clearInvalid() {
  props.question.routing = { rules: [], default_target: null };
}
function add() {
  const q = props.question;
  if (!operators[q.type]) return;
  q.routing.rules.push({
    condition: {
      question_id: q.id,
      operator: operators[q.type][0].id,
      value:
        q.type === "number"
          ? 0
          : q.type === "multiple_choice"
            ? [q.options[0]?.id]
            : q.options[0]?.id,
    },
    target: "END",
  });
}
function source(c: Condition) {
  return props.questions.find((q) => q.id === c.question_id);
}
function reset(c: Condition) {
  const q = source(c);
  if (!q) return;
  c.operator = operators[q.type]?.[0].id;
  c.value =
    q.type === "number"
      ? 0
      : q.type === "multiple_choice"
        ? [q.options[0]?.id]
        : q.options[0]?.id;
}
function changeOp(c: Condition) {
  const q = source(c);
  if (q?.type === "number") c.value = c.operator === "between" ? [0, 100] : 0;
}
</script>
<template>
  <div class="routing-panel">
    <div class="inline-heading">
      <strong>条件跳转</strong
      ><button
        type="button"
        class="text-button"
        @click="add"
        :disabled="
          !!structuralProblem ||
          !operators[question.type] ||
          safeRules.length >= 20
        "
      >
        ＋ 添加规则
      </button>
    </div>
    <p class="input-hint">
      按优先级采用第一条满足的规则，仅跳往后续题目。文本题可设置默认去向。
    </p>
    <div v-if="structuralProblem" class="alert error" role="alert">
      跳转配置损坏：{{ structuralProblem }}。请使用高级 JSON 修正或<button
        type="button"
        class="text-button"
        @click="clearInvalid"
      >
        清空损坏的跳转配置</button
      >。
    </div>
    <div v-for="(rule, ri) in safeRules" :key="ri" class="rule-row">
      <span class="rule-number">{{ ri + 1 }}</span
      ><template v-if="!rule.condition.all && !rule.condition.any"
        ><select
          aria-label="条件来源题目"
          v-model="rule.condition.question_id"
          @change="reset(rule.condition)"
        >
          <option
            v-for="(q, qi) in questions
              .slice(0, index + 1)
              .filter((q) => operators[q.type])"
            :value="q.id"
          >
            {{ questions.indexOf(q) + 1 }}. {{ q.title || "未命名题目" }}
          </option></select
        ><select
          aria-label="条件运算符"
          v-model="rule.condition.operator"
          @change="changeOp(rule.condition)"
        >
          <option
            v-for="op in operators[source(rule.condition)?.type || ''] || []"
            :value="op.id"
          >
            {{ op.name }}
          </option></select
        ><template v-if="source(rule.condition)?.type === 'number'"
          ><template v-if="rule.condition.operator === 'between'"
            ><input
              type="number"
              v-model.number="rule.condition.value[0]"
              aria-label="区间下界" /><input
              type="number"
              v-model.number="rule.condition.value[1]"
              aria-label="区间上界" /></template
          ><input
            v-else
            type="number"
            v-model.number="rule.condition.value"
            aria-label="比较数值" /></template
        ><select
          v-else
          :multiple="source(rule.condition)?.type === 'multiple_choice'"
          v-model="rule.condition.value"
          aria-label="条件选项"
        >
          <option v-for="o in source(rule.condition)?.options" :value="o.id">
            {{ o.label }}
          </option>
        </select></template
      ><span v-else>组合条件已配置（可在规则 JSON 中编辑）</span><span>→</span
      ><select v-model="rule.target" aria-label="跳转目标">
        <option v-for="(q, qi) in questions.slice(index + 1)" :value="q.id">
          {{ index + qi + 2 }}. {{ q.title || "未命名题目" }}
        </option>
        <option value="END">结束问卷</option></select
      ><button
        type="button"
        class="icon-button danger-text"
        @click="question.routing.rules.splice(ri, 1)"
        aria-label="删除规则"
      >
        ×
      </button>
    </div>
    <label v-if="!structuralProblem" class="inline-field"
      >未匹配时<select v-model="question.routing.default_target">
        <option :value="null">按顺序进入下一题</option>
        <option v-for="(q, qi) in questions.slice(index + 1)" :value="q.id">
          {{ index + qi + 2 }}. {{ q.title || "未命名题目" }}
        </option>
        <option value="END">结束问卷</option>
      </select></label
    >
  </div>
</template>
