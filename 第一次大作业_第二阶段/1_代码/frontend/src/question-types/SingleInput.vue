<script setup lang="ts">
import type { Question } from "../types";
defineProps<{ question: Question; modelValue: any }>();
const emit = defineEmits(["update:modelValue"]);
</script>
<template>
  <label
    v-for="o in question.options"
    :key="o.id"
    class="answer-option"
    :class="{ selected: modelValue === o.id }"
    ><input
      type="radio"
      :name="question.id"
      :value="o.id"
      :checked="modelValue === o.id"
      @change="emit('update:modelValue', o.id)"
    /><span>{{ o.label }}</span></label
  >
</template>
