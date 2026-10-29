<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
import QuestionUsage from "../components/QuestionUsage.vue";
const qid = String(useRoute().params.id),
  data = ref<any>(null),
  error = ref(""),
  busy = ref(false),
  left = ref(""),
  right = ref(""),
  changes = ref<any[]>([]);
async function load() {
  try {
    data.value = await api(`/questions/${qid}`);
    left.value = data.value.versions[0]?._id || "";
    right.value = data.value.versions.at(-1)?._id || "";
  } catch (e: any) {
    error.value = e.message;
  }
}
async function compare() {
  try {
    changes.value = await api(
      `/question-versions/${left.value}/diff/${right.value}`,
    );
  } catch (e: any) {
    error.value = e.message;
  }
}
async function restore(v: any) {
  if (busy.value || !data.value || data.value.question.archived) return;
  if (
    !confirm(
      `基于当前最近版本创建新版本，内容恢复自v${v.version}？旧版本全部保留。`,
    )
  )
    return;
  busy.value = true;
  try {
    await api(`/questions/${qid}/restore`, "POST", {
      revision: data.value.question.revision,
      parent_version_id: data.value.question.latest_version_id,
      restored_from_version_id: v._id,
      change_note: `恢复v${v.version}`,
    });
    await load();
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
const label = (id: string) =>
  data.value.versions.find((v: any) => v._id === id)?.version ?? "无";
onMounted(load);
</script>
<template>
  <main class="page">
    <router-link to="/questions">← 题目管理</router-link>
    <h1>版本历史</h1>
    <p v-if="error" class="alert error">{{ error }}</p>
    <template v-if="data"
      ><article
        class="panel phase2-card"
        v-for="v in data.versions"
        :key="v._id"
      >
        <h2>v{{ v.version }} · {{ v.content.title }}</h2>
        <p>
          父版本：{{
            v.parent_version_id ? "v" + label(v.parent_version_id) : "无"
          }}
          <span v-if="v.restored_from_version_id"
            >· 内容恢复自v{{ label(v.restored_from_version_id) }}</span
          >
        </p>
        <p class="muted">
          {{ v.change_note }} · {{ new Date(v.created_at).toLocaleString() }}
        </p>
        <div class="actions">
          <router-link
            class="button"
            :to="`/questions/${qid}/edit?base=${v._id}`"
            v-if="!data.question.archived"
            >基于此版修改</router-link
          ><button
            class="button"
            :disabled="busy || data.question.archived"
            @click="restore(v)"
          >
            恢复此版内容</button
          ><router-link
            class="button"
            :to="`/question-versions/${v._id}/statistics`"
            >统计</router-link
          >
        </div>
      </article>
      <section class="panel phase2-card">
        <h2>版本比较</h2>
        <div class="actions">
          <select v-model="left" aria-label="原版本">
            <option v-for="v in data.versions" :value="v._id">
              v{{ v.version }}
            </option></select
          ><span>→</span
          ><select v-model="right" aria-label="目标版本">
            <option v-for="v in data.versions" :value="v._id">
              v{{ v.version }}
            </option></select
          ><button class="button" @click="compare">比较</button>
        </div>
        <p v-if="!changes.length" class="muted">暂无差异结果。</p>
        <div v-for="c in changes">
          <h3>{{ c.field }}</h3>
          <pre
            >{{ JSON.stringify(c.before, null, 2) }}
→ {{ JSON.stringify(c.after, null, 2) }}</pre
          >
        </div>
      </section>
      <section class="panel phase2-card">
        <QuestionUsage :question-id="qid" /></section
    ></template>
  </main>
</template>
