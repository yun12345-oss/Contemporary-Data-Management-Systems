<script setup lang="ts">
import { ref } from "vue";
import { api } from "../api";
const props = defineProps<{ versionId: string; surveyId?: string }>();
const emit = defineEmits<{ changed: [] }>();
const username = ref(""),
  busy = ref(false),
  error = ref(""),
  message = ref("");
async function share() {
  busy.value = true;
  error.value = "";
  message.value = "";
  try {
    await api("/grants", "POST", {
      kind: props.surveyId ? "aggregate" : "use",
      question_version_id: props.versionId,
      username: username.value,
      ...(props.surveyId ? { survey_id: props.surveyId } : {}),
    });
    message.value = "已授权，仅适用于此确定版本";
    emit("changed");
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <form @submit.prevent="share" class="phase2-sharing">
    <label
      >{{ surveyId ? "授权此问卷该版本的汇总统计" : "共享此版本的使用权"
      }}<input
        v-model="username"
        required
        minlength="3"
        maxlength="40"
        placeholder="接收者用户名" /></label
    ><button class="button" :disabled="busy">
      {{ busy ? "处理中…" : "授权" }}
    </button>
    <p class="input-hint">
      {{
        surveyId
          ? "不开放原始答案；可在共享管理撤销。"
          : "不包含未来版本、修改权、再共享权或答卷访问权。"
      }}
    </p>
    <p class="alert error" v-if="error">{{ error }}</p>
    <p class="alert success" v-if="message">{{ message }}</p>
  </form>
</template>
