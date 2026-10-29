<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "../api";
import { typeNames } from "../types";
import QuestionSharing from "../components/QuestionSharing.vue";
const data = ref<any>({ items: [], total: 0 }),
  page = ref(1),
  search = ref(""),
  error = ref(""),
  busy = ref(false);
async function load() {
  busy.value = true;
  error.value = "";
  try {
    data.value = await api(
      `/questions?page=${page.value}&search=${encodeURIComponent(search.value)}`,
    );
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
async function archive(q: any) {
  if (!confirm("归档后停止新增使用；历史版本及既有合法实例保留。继续？"))
    return;
  try {
    await api(`/questions/${q._id}/archive`, "POST", { revision: q.revision });
    await load();
  } catch (e: any) {
    error.value = e.message;
  }
}
onMounted(load);
</script>
<template>
  <main class="page">
    <div class="editor-header">
      <div>
        <span class="eyebrow">REUSABLE QUESTIONS</span>
        <h1>题目管理</h1>
        <p class="muted">版本固定，历史独立。共享只授予指定版本的使用权。</p>
      </div>
      <router-link class="button primary" to="/questions/new"
        >创建题目</router-link
      >
    </div>
    <div class="actions">
      <input
        v-model="search"
        placeholder="搜索题目"
        @keyup.enter="
          page = 1;
          load();
        "
      /><button
        class="button"
        :disabled="busy"
        @click="
          page = 1;
          load();
        "
      >
        搜索
      </button>
    </div>
    <p class="alert error" v-if="error">{{ error }}</p>
    <p v-if="busy">正在加载…</p>
    <article class="panel phase2-card" v-for="q in data.items" :key="q._id">
      <div class="editor-header">
        <h2>
          {{ q.title }}
          <small
            >{{ q.owned ? "我的题目" : "共享给我"
            }}{{ q.archived ? " · 已归档" : "" }}</small
          >
        </h2>
        <div class="actions">
          <router-link class="button" :to="`/questions/${q._id}/usage`"
            >使用情况</router-link
          >
          <template v-if="q.owned">
            <router-link class="button" :to="`/questions/${q._id}/history`"
              >历史与使用</router-link
            ><button class="button" :disabled="q.archived" @click="archive(q)">
              归档
            </button>
          </template>
        </div>
      </div>
      <div class="phase2-version" v-for="v in q.versions" :key="v._id">
        <div>
          <strong>v{{ v.version }} · {{ v.content.title }}</strong>
          <p class="muted">
            {{ typeNames[v.content.type] }} · {{ v.change_note }}
          </p>
        </div>
        <div class="actions">
          <router-link
            class="button"
            v-if="q.owned && !q.archived"
            :to="`/questions/${q._id}/edit?base=${v._id}`"
            >基于此版修改</router-link
          ><router-link
            class="button"
            :to="`/question-versions/${v._id}/statistics`"
            >单题统计</router-link
          >
        </div>
        <QuestionSharing v-if="q.owned && !q.archived" :version-id="v._id" />
      </div>
    </article>
    <p class="panel" v-if="!busy && !data.items.length">
      尚无题目。创建题目，或从问卷中保存常用题。
    </p>
    <div class="actions">
      <button
        class="button"
        :disabled="page <= 1 || busy"
        @click="
          page--;
          load();
        "
      >
        上一页</button
      ><span>{{ page }} / {{ Math.max(1, Math.ceil(data.total / 20)) }}</span
      ><button
        class="button"
        :disabled="page * 20 >= data.total || busy"
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
