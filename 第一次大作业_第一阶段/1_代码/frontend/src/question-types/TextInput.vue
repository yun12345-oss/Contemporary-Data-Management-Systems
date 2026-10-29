<script setup lang="ts">
import { ref, computed, watch } from "vue";
import type { Question } from "../types";
import { textLength } from "../text";
const props = defineProps<{ question: Question; modelValue: any }>();
const emit = defineEmits<{ "update:modelValue": [value: string] }>();
const raw = ref(String(props.modelValue ?? "")),
  composing = ref(false);
let lastEmitted = raw.value;
const limit = computed(() => props.question.validation.max_length ?? 10000);
const count = computed(() => textLength(raw.value));
watch(
  () => props.modelValue,
  (value) => {
    if (!composing.value) {
      raw.value = String(value ?? "");
      lastEmitted = raw.value;
    }
  },
);
watch(
  () => props.question.id,
  () => {
    composing.value = false;
    raw.value = String(props.modelValue ?? "");
    lastEmitted = raw.value;
  },
);
function commit() {
  if (raw.value !== lastEmitted) {
    lastEmitted = raw.value;
    emit("update:modelValue", raw.value);
  }
}
function input(event: Event) {
  raw.value = (event.target as HTMLTextAreaElement).value;
  if (!composing.value && !(event as InputEvent).isComposing) commit();
}
function compositionEnd(event: Event) {
  composing.value = false;
  raw.value = (event.target as HTMLTextAreaElement).value;
  commit();
}
</script>
<template>
  <textarea
    :value="raw"
    @input="input"
    @compositionstart="composing = true"
    @compositionend="compositionEnd"
    rows="4"
    placeholder="请填写你的回答"
    :aria-label="question.title || '文本回答'"
    :aria-invalid="!composing && count > limit"
    :aria-describedby="`${question.id}-text-count`"
  ></textarea>
  <p class="input-hint" :id="`${question.id}-text-count`" aria-live="polite">
    {{
      composing
        ? "正在输入…"
        : `${count} / ${limit} 字符（去首尾空白，按 Unicode 码点）`
    }}
  </p>
  <p v-if="!composing && count > limit" class="field-error" role="alert">
    文本超出允许长度，内容已保留，请缩短后继续。
  </p>
</template>
