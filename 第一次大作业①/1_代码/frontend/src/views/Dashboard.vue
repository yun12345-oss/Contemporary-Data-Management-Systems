<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { api } from "../api";
import { type Survey, dateLabel } from "../types";
const router = useRouter(),
  items = ref<Survey[]>([]),
  total = ref(0),
  page = ref(1),
  loading = ref(true),
  error = ref(""),
  search = ref(""),
  filter = ref("all"),
  creating = ref(false),
  toast = ref("");
const shown = computed(() =>
  items.value.filter(
    (s) =>
      (filter.value === "all" || s.status === filter.value) &&
      s.draft.title.toLowerCase().includes(search.value.toLowerCase()),
  ),
);
const responses = computed(() =>
  items.value.reduce((n, s) => n + (s.response_count || 0), 0),
);
async function load() {
  loading.value = true;
  try {
    const d = await api(`/surveys?page=${page.value}`);
    items.value = d.items;
    total.value = d.total;
    error.value = "";
  } catch (e: any) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}
async function create() {
  creating.value = true;
  try {
    const s = await api("/surveys", "POST", { title: "未命名问卷" });
    await router.push(`/surveys/${s._id}/edit`);
  } catch (e: any) {
    error.value = e.message;
  } finally {
    creating.value = false;
  }
}
async function copy(s: Survey) {
  try {
    await navigator.clipboard.writeText(
      `${location.origin}/survey/${s.share_code}`,
    );
    toast.value = "填写链接已复制";
    setTimeout(() => (toast.value = ""), 2500);
  } catch {
    toast.value = `填写链接：${location.origin}/survey/${s.share_code}`;
  }
}
function state(s: Survey) {
  return s.status === "published" &&
    s.deadline &&
    new Date(s.deadline) < new Date()
    ? "已截止"
    : ({ draft: "草稿", published: "收集中", closed: "已关闭" } as any)[
        s.status
      ];
}
onMounted(load);
</script>
<template>
  <main class="page dashboard">
    <div class="page-heading">
      <div>
        <span class="eyebrow">WORKSPACE / 我的问卷</span>
        <h1>从一个好问题开始<span class="accent-dot">.</span></h1>
        <p class="muted">设计、分享、发现。你的每一份问卷，都在这里。</p>
      </div>
      <button class="button primary" @click="create" :disabled="creating">
        ＋ 创建问卷
      </button>
    </div>
    <section class="overview">
      <div class="overview-intro">
        <span class="eyebrow">YOUR RESEARCH, AT A GLANCE</span>
        <h2>每个回答，<br />都让发现更近一步。</h2>
        <div class="mini-line"></div>
      </div>
      <div class="metric">
        <span>全部问卷</span
        ><strong>{{ String(total).padStart(2, "0") }}</strong
        ><small>持续积累你的问题</small>
      </div>
      <div class="metric">
        <span>本页收集中</span
        ><strong>{{
          String(
            items.filter(
              (s) =>
                s.status === "published" &&
                (!s.deadline || new Date(s.deadline) > new Date()),
            ).length,
          ).padStart(2, "0")
        }}</strong
        ><small>等待新的回答</small>
      </div>
      <div class="metric">
        <span>本页累计提交</span><strong>{{ responses }}</strong
        ><small>每一次反馈都值得被看见</small>
      </div>
    </section>
    <div class="section-toolbar">
      <div class="tabs">
        <button
          v-for="tab in [
            { id: 'all', name: '全部问卷' },
            { id: 'published', name: '已发布' },
            { id: 'draft', name: '草稿' },
            { id: 'closed', name: '已关闭' },
          ]"
          :class="{ active: filter === tab.id }"
          @click="filter = tab.id"
        >
          {{ tab.name }}
        </button>
      </div>
      <input
        class="search"
        v-model="search"
        aria-label="搜索本页问卷"
        placeholder="搜索本页问卷…"
      />
    </div>
    <div v-if="error" class="alert error">
      {{ error }} <button class="text-button" @click="load">重试</button>
    </div>
    <div v-if="toast" class="toast" role="status">{{ toast }}</div>
    <div v-if="loading" class="empty-state">正在加载问卷…</div>
    <section class="survey-grid" v-else>
      <article v-for="(s, i) in shown" :key="s._id" class="survey-card">
        <div class="card-top">
          <span class="survey-icon">▤</span
          ><span class="badge" :class="s.status">{{ state(s) }}</span>
        </div>
        <router-link :to="`/surveys/${s._id}/edit`" class="card-title">{{
          s.draft.title
        }}</router-link>
        <p class="card-description">
          {{ s.draft.description || "为你的下一次发现，写下第一个问题。" }}
        </p>
        <div class="card-meta">
          <span>{{ s.draft.questions.length }} 道题目</span
          ><span>{{ s.response_count || 0 }} 份提交</span
          ><span>{{
            s.current_version ? "v" + s.current_version : "未发布"
          }}</span>
        </div>
        <div class="card-bottom">
          <small>更新于 {{ dateLabel(s.updated_at) }}</small>
          <div>
            <router-link :to="`/surveys/${s._id}/edit`" class="text-button"
              >编辑</router-link
            ><router-link
              v-if="s.current_version"
              :to="`/surveys/${s._id}/statistics`"
              class="text-button"
              >统计 ↗</router-link
            ><button
              v-if="s.current_version"
              class="icon-button"
              @click="copy(s)"
              title="复制填写链接"
              aria-label="复制填写链接"
            >
              ↗
            </button>
          </div>
        </div>
      </article>
      <button class="new-survey-card" @click="create" :disabled="creating">
        <span>＋</span><strong>创建下一份问卷</strong
        ><small>让新的想法成为新的发现</small>
      </button>
    </section>
    <div v-if="!loading && shown.length === 0 && items.length" class="muted">
      本页没有匹配的问卷。
    </div>
    <div class="pagination" v-if="total > 20">
      <button
        class="button"
        :disabled="page === 1"
        @click="
          page--;
          load();
        "
      >
        上一页</button
      ><span>第 {{ page }} 页 / 共 {{ Math.ceil(total / 20) }} 页</span
      ><button
        class="button"
        :disabled="page * 20 >= total"
        @click="
          page++;
          load();
        "
      >
        下一页
      </button>
    </div>
    <div class="workspace-note">
      <span>✳</span>
      <p>
        <strong>让问卷按回答自然展开。</strong>
        为题目配置跳转条件，把不同的回答带到合适的问题。
      </p>
      <span class="note-tag">设计小提示</span>
    </div>
  </main>
</template>
