<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router";
import { api } from "../api";
import QuestionContentEditor from "../components/QuestionContentEditor.vue";
const route = useRoute(),
  router = useRouter(),
  qid = String(route.params.id || "");
const content = ref<any>({
    type: "number",
    title: "",
    options: [],
    validation: {},
  }),
  note = ref(""),
  revision = ref(0),
  parent = ref(""),
  saved = ref(""),
  error = ref(""),
  busy = ref(false),
  ready = ref(!qid);
const snapshot = () =>
  JSON.stringify({ content: content.value, note: note.value });
saved.value = snapshot();
function leave() {
  return (
    !busy.value &&
    (snapshot() === saved.value || confirm("题目修改尚未保存，确认离开？"))
  );
}
function unload(e: BeforeUnloadEvent) {
  if (busy.value || snapshot() !== saved.value) {
    e.preventDefault();
    e.returnValue = "";
  }
}
onBeforeRouteLeave(leave);
onBeforeUnmount(() => window.removeEventListener("beforeunload", unload));
onMounted(async () => {
  window.addEventListener("beforeunload", unload);
  if (!qid) return;
  try {
    const data = await api(`/questions/${qid}`);
    revision.value = data.question.revision;
    parent.value = String(route.query.base || data.question.latest_version_id);
    const v = data.versions.find((v: any) => v._id === parent.value);
    if (!v) throw new Error("指定父版本不存在");
    content.value = JSON.parse(JSON.stringify(v.content));
    saved.value = snapshot();
    ready.value = true;
  } catch (e: any) {
    error.value = e.message;
  }
});
async function save() {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    const data = await api(
      qid ? `/questions/${qid}/versions` : "/questions",
      "POST",
      {
        content: content.value,
        change_note: note.value || "更新题目",
        ...(qid
          ? { revision: revision.value, parent_version_id: parent.value }
          : {}),
      },
    );
    saved.value = snapshot();
    busy.value = false;
    await router.push(`/questions/${data.question._id}/history`);
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <main class="page phase2-narrow">
    <router-link to="/questions">← 题目管理</router-link>
    <h1>{{ qid ? "创建新版本" : "创建常用题目" }}</h1>
    <p class="muted">旧版本不修改，最近创建版本也不会自动替换任何问卷。</p>
    <p class="alert error" v-if="error">{{ error }}</p>
    <form v-if="ready" @submit.prevent="save" class="panel">
      <fieldset :disabled="busy">
        <QuestionContentEditor :content="content" /><label
          >修改说明<textarea v-model="note" maxlength="1000" rows="2" /></label
        ><button class="button primary">
          {{ busy ? "保存中…" : "保存不可变版本" }}
        </button>
      </fieldset>
    </form>
  </main>
</template>
