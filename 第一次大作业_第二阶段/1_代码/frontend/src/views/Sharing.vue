<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api, auth } from "../api";
const data = ref<any>({ items: [], total: 0 }),
  page = ref(1),
  error = ref(""),
  busy = ref(false);
async function load() {
  try {
    data.value = await api(`/grants?page=${page.value}`);
  } catch (e: any) {
    error.value = e.message;
  }
}
async function revoke(g: any) {
  if (
    !confirm(
      "撤销后停止新增使用或汇总读取。既有合法问卷实例不受使用授权撤销影响。继续？",
    )
  )
    return;
  busy.value = true;
  try {
    await api(`/grants/${g._id}/revoke`, "POST", { revision: g.revision });
    await load();
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
onMounted(load);
</script>
<template>
  <main class="page">
    <h1>共享与授权</h1>
    <p class="muted">
      使用权不包含派生、转授或答卷访问。汇总统计权由问卷所有者单独授予。
    </p>
    <p v-if="error" class="alert error">{{ error }}</p>
    <article v-for="g in data.items" class="panel phase2-card" :key="g._id">
      <h2>
        {{ g.kind === "use" ? "指定版本使用权" : "指定问卷、版本的汇总统计权" }}
        · {{ g.active ? "有效" : "已撤销" }}
      </h2>
      <p>{{ g.grantor_username }} → {{ g.grantee_username }}</p>
      <p class="input-hint">
        版本ID：{{ g.question_version_id
        }}<span v-if="g.survey_id"> · 问卷ID：{{ g.survey_id }}</span>
      </p>
      <router-link
        v-if="
          g.active && g.kind === 'aggregate' && g.grantee_id === auth.user?.id
        "
        class="button primary"
        :to="{
          path: `/question-versions/${g.question_version_id}/statistics`,
          query: { survey_id: g.survey_id },
        }"
        >查看授权统计</router-link
      >
      <button
        class="button"
        v-if="g.active && g.grantor_id === auth.user?.id"
        :disabled="busy"
        @click="revoke(g)"
      >
        撤销授权
      </button>
    </article>
    <p v-if="!data.items.length">
      暂无授权记录。可在题目管理共享指定版本，或在问卷编辑器授予汇总统计权限。
    </p>
    <div class="actions">
      <button
        class="button"
        :disabled="page <= 1"
        @click="
          page--;
          load();
        "
      >
        上一页</button
      ><span>{{ page }} / {{ Math.max(1, Math.ceil(data.total / 20)) }}</span
      ><button
        class="button"
        :disabled="page * 20 >= data.total"
        @click="
          page++;
          load();
        "
      >
        下一页
      </button>
    </div>
  </main>
</template>
