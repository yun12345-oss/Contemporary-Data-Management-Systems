<script setup lang="ts">
import type { Question } from "../types";
import { inputComponents } from "../question-types/registry";
defineProps<{ question: Question; modelValue: any; error?: string }>();
const emit = defineEmits(["update:modelValue"]);
</script>
<template>
  <div class="question-input">
    <component
      :is="inputComponents[question.type]"
      v-if="inputComponents[question.type]"
      :question="question"
      :model-value="modelValue"
      @update:model-value="emit('update:modelValue', $event)"
    />
    <p v-else class="field-error">当前界面不支持该题型</p>
    <p class="field-error" v-if="error" role="alert">{{ error }}</p>
    <p class="input-hint" v-if="question.type === 'multiple_choice'">
      {{
        question.validation.min_choices
          ? "至少选择 " + question.validation.min_choices + " 项。"
          : ""
      }}{{
        question.validation.max_choices
          ? "最多选择 " + question.validation.max_choices + " 项。"
          : ""
      }}
    </p>
    <p class="input-hint" v-if="question.type === 'text'">
      {{
        question.validation.min_length
          ? "至少 " + question.validation.min_length + " 字。"
          : ""
      }}{{
        question.validation.max_length
          ? "最多 " + question.validation.max_length + " 字。"
          : ""
      }}
    </p>
    <p class="input-hint" v-if="question.type === 'number'">
      {{ question.validation.integer_only ? "仅限整数。" : ""
      }}{{
        question.validation.min !== undefined
          ? "最小值 " + question.validation.min + "。"
          : ""
      }}{{
        question.validation.max !== undefined
          ? "最大值 " + question.validation.max + "。"
          : ""
      }}
    </p>
  </div>
</template>
