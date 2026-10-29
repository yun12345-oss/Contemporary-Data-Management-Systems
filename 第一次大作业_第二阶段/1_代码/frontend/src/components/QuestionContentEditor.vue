<script setup lang="ts">
import { makeId, typeNames } from "../types";
const props = defineProps<{ content: any; lockedType?: boolean }>();
function changeType() {
  props.content.validation = {};
  props.content.options = ["single_choice", "multiple_choice"].includes(
    props.content.type,
  )
    ? [
        { id: makeId("o"), label: "选项1" },
        { id: makeId("o"), label: "选项2" },
      ]
    : [];
}
function setNumber(key: string, event: Event) {
  const raw = (event.target as HTMLInputElement).value;
  if (raw === "") delete props.content.validation[key];
  else props.content.validation[key] = Number(raw);
}
</script>
<template>
  <div class="phase2-form">
    <label
      >题型<select v-model="content.type" @change="changeType">
        <option v-for="(name, key) in typeNames" :value="key">
          {{ name }}
        </option>
      </select></label
    >
    <label
      >题目标题<input
        v-model="content.title"
        maxlength="500"
        placeholder="输入清楚、稳定的题目含义"
    /></label>
    <template
      v-if="['single_choice', 'multiple_choice'].includes(content.type)"
    >
      <label>选项</label>
      <div
        class="option-edit"
        v-for="(option, index) in content.options"
        :key="option.id"
      >
        <input
          v-model="option.label"
          maxlength="200"
          :aria-label="'选项' + (index + 1)"
        /><button
          type="button"
          class="button"
          :disabled="content.options.length <= 2"
          @click="content.options.splice(index, 1)"
        >
          删除
        </button>
      </div>
      <button
        type="button"
        class="button"
        :disabled="content.options.length >= 100"
        @click="content.options.push({ id: makeId('o'), label: '新选项' })"
      >
        添加选项
      </button>
    </template>
    <div class="validation-grid" v-if="content.type === 'multiple_choice'">
      <label
        v-for="(name, key) in {
          min_choices: '最少选择',
          max_choices: '最多选择',
        }"
        >{{ name
        }}<input
          type="number"
          min="0"
          :value="content.validation[key] ?? ''"
          @input="setNumber(key, $event)"
          placeholder="不限制"
      /></label>
    </div>
    <div class="validation-grid" v-if="content.type === 'text'">
      <label
        v-for="(name, key) in {
          min_length: '最少字符',
          max_length: '最多字符',
        }"
        >{{ name
        }}<input
          type="number"
          min="0"
          :value="content.validation[key] ?? ''"
          @input="setNumber(key, $event)"
          placeholder="不限制"
      /></label>
    </div>
    <template v-if="content.type === 'number'"
      ><div class="validation-grid">
        <label v-for="(name, key) in { min: '最小值', max: '最大值' }"
          >{{ name
          }}<input
            type="number"
            :value="content.validation[key] ?? ''"
            @input="setNumber(key, $event)"
            placeholder="不限制"
        /></label>
      </div>
      <label class="checkbox-label"
        ><input
          type="checkbox"
          v-model="content.validation.integer_only"
        />仅整数</label
      ></template
    >
    <p class="input-hint">
      保存产生不可变版本；必答与跳转在具体问卷中配置。修改选项文字不会自动改变选项ID，请保持语义一致。
    </p>
  </div>
</template>
