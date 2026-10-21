import type { Component } from "vue";
import SingleInput from "./SingleInput.vue";
import MultipleInput from "./MultipleInput.vue";
import TextInput from "./TextInput.vue";
import NumberInput from "./NumberInput.vue";
export const inputComponents: Record<string, Component> = {
  single_choice: SingleInput,
  multiple_choice: MultipleInput,
  text: TextInput,
  number: NumberInput,
};
