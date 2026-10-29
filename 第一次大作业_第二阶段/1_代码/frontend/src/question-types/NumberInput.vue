<script setup lang="ts">
import type { Question } from "../types";
defineProps<{ question: Question; modelValue: any }>();
const emit = defineEmits(["update:modelValue"]);
</script>
<template>
  <input
    type="text"
    inputmode="decimal"
    :value="modelValue ?? ''"
    @input="
      emit('update:modelValue', ($event.target as HTMLInputElement).value)
    "
    :aria-label="question.title"
    placeholder="请输入数字"
  />
</template>
