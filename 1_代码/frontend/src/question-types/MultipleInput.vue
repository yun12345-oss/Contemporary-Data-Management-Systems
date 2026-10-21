<script setup lang="ts">
import { computed } from "vue";
import type { Question } from "../types";
const props = defineProps<{ question: Question; modelValue: any }>(),
  emit = defineEmits(["update:modelValue"]);
const selected = computed<string[]>(() =>
  Array.isArray(props.modelValue) ? props.modelValue : [],
);
function toggle(id: string) {
  emit(
    "update:modelValue",
    selected.value.includes(id)
      ? selected.value.filter((x) => x !== id)
      : [...selected.value, id],
  );
}
</script>
<template>
  <label
    v-for="o in question.options"
    :key="o.id"
    class="answer-option"
    :class="{ selected: selected.includes(o.id) }"
    ><input
      type="checkbox"
      :checked="selected.includes(o.id)"
      @change="toggle(o.id)"
    /><span>{{ o.label }}</span></label
  >
</template>
