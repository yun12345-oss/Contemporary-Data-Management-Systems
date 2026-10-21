<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
import { typeNames, dateLabel } from "../types";
import { optionCount, optionPercent, type CountBasis } from "../statistics";
const route = useRoute(),
  sid = String(route.params.id),
  versions = ref<any[]>([]),
  version = ref(0),
  stats = ref<any>(null),
  error = ref(""),
  busy = ref(false),
  selected = ref("all"),
  start = ref(""),
  end = ref(""),
  values = ref<any>(null),
  valueQ = ref<any>(null),
  page = ref(1),
  basis = ref<CountBasis>("responses");
const shown = computed(
  () =>
    stats.value?.questions.filter(
      (q: any) => selected.value === "all" || q.id === selected.value,
    ) || [],
);
function query() {
  const p = new URLSearchParams({ version: String(version.value) });
  if (start.value) p.set("start", new Date(start.value).toISOString());
  if (end.value) p.set("end", new Date(end.value).toISOString());
  return p.toString();
}
async function load() {
  busy.value = true;
  error.value = "";
  try {
    stats.value = await api(`/surveys/${sid}/statistics?${query()}`);
  } catch (e: any) {
    error.value = e.message;
    stats.value = null;
  } finally {
    busy.value = false;
  }
}
async function showValues(q: any, p = 1) {
  try {
    page.value = p;
    valueQ.value = q;
    values.value = await api(
      `/surveys/${sid}/questions/${q.id}/values?${query()}&page=${p}`,
    );
  } catch (e: any) {
    error.value = e.message;
  }
}
onMounted(async () => {
  try {
    versions.value = await api(`/surveys/${sid}/versions`);
    version.value = versions.value[0]?.version || 0;
    if (version.value) await load();
    else error.value = "发布问卷后即可查看统计";
  } catch (e: any) {
    error.value = e.message;
  }
});
</script>
<template>
  <main class="page stats-page">
    <router-link class="breadcrumb" to="/">← 我的问卷</router-link>
    <div class="page-heading">
      <div>
        <span class="eyebrow">RESULTS & INSIGHTS</span>
        <h1>让回答，成为发现<span class="accent-dot">.</span></h1>
        <p class="muted">
          {{ stats?.title || "问卷统计" }} · 数据实时计算，历史版本独立保留
        </p>
      </div>
      <router-link class="button" :to="`/surveys/${sid}/edit`"
        >返回编辑</router-link
      >
    </div>
    <section class="panel stats-filters">
      <label
        >发布版本<select
          v-model="version"
          @change="
            selected = 'all';
            load();
          "
        >
          <option v-for="v in versions" :value="v.version">
            v{{ v.version }} · {{ dateLabel(v.published_at) }}
          </option>
        </select></label
      ><label>开始时间<input type="datetime-local" v-model="start" /></label
      ><label>结束时间<input type="datetime-local" v-model="end" /></label
      ><button class="button primary" :disabled="busy" @click="load">
        应用筛选</button
      ><label
        >题目<select v-model="selected">
          <option value="all">全部题目</option>
          <option v-for="q in stats?.questions" :value="q.id">
            {{ q.title }}
          </option>
        </select></label
      >
    </section>
    <label class="stats-basis"
      >选项统计口径
      <select v-model="basis" aria-label="选项统计口径">
        <option value="responses">按作答次数</option>
        <option value="people">按去重人数</option>
      </select>
    </label>
    <div class="alert error" v-if="error">{{ error }}</div>
    <div class="empty-state" v-if="busy">正在计算统计…</div>
    <template v-else-if="stats"
      ><div class="stats-summary">
        <div>
          <span class="eyebrow">TOTAL RESPONSES</span
          ><strong>{{ stats.total }}</strong
          ><span>份有效提交</span>
        </div>
        <div>
          <strong>{{ stats.respondent_count }}</strong
          ><span>人填写（去重账号）</span>
        </div>
        <div>
          <strong>{{ stats.questions.length }}</strong
          ><span>道题目</span>
        </div>
        <div>
          <strong>v{{ stats.version }}</strong
          ><span>当前统计版本</span>
        </div>
        <p>
          人数在所选版本和时间范围内按账号去重，匿名与实名合并计数。<br />
          {{
            basis === "people"
              ? "百分比以该题去重作答人数为分母。重复填写时，单选各项人数也可能交叉。"
              : "百分比以该题有效作答次数为分母。"
          }}<br />
          跳过或空白不计入该题；各选项百分比之和可能超过 100%。
        </p>
      </div>
      <section class="stats-grid">
        <article class="panel question-stats" v-for="q in shown" :key="q.id">
          <div class="inline-heading">
            <span class="badge">{{ typeNames[q.type] }}</span
            ><span class="muted"
              >{{ q.answered }} 次作答 · {{ q.respondent_count }} 人</span
            >
          </div>
          <h2>{{ q.title }}</h2>
          <template v-if="q.options"
            ><div class="bar-row" v-for="o in q.options">
              <div>
                <span>{{ o.label }}</span
                ><strong
                  >{{ optionCount(o, basis) }}
                  {{ basis === "people" ? "人" : "次" }}
                  <small>{{ o.count }} 次 / {{ o.respondent_count }} 人</small>
                  <small
                    >{{ optionPercent(o, q, basis).toFixed(1) }}%</small
                  ></strong
                >
              </div>
              <div class="bar-track">
                <span
                  :style="{
                    width: optionPercent(o, q, basis) + '%',
                  }"
                ></span>
              </div></div></template
          ><template v-else-if="q.type === 'number'"
            ><div class="numeric-result">
              <span
                >平均值（按作答次数）<strong>{{
                  q.average === null ? "—" : Number(q.average.toFixed(2))
                }}</strong></span
              ><span
                >最小值<strong>{{ q.min ?? "—" }}</strong></span
              ><span
                >最大值<strong>{{ q.max ?? "—" }}</strong></span
              >
            </div>
            <button class="text-button" @click="showValues(q)">
              查看所有回答 ↗
            </button></template
          ><template v-else
            ><p class="muted">
              {{
                q.answered
                  ? "每一段文字，都是一个值得倾听的声音。"
                  : "还没有收到这道题的回答。"
              }}
            </p>
            <button class="button" @click="showValues(q)">
              查看填写内容 ↗
            </button></template
          >
        </article>
      </section>
      <div class="panel empty-state" v-if="!stats.total">
        还没有提交记录。分享问卷链接，邀请第一位填写者。
      </div></template
    >
    <div class="modal-backdrop" v-if="values" @click.self="values = null">
      <section
        class="modal"
        role="dialog"
        aria-modal="true"
        aria-label="填写内容"
      >
        <button
          class="modal-close icon-button"
          @click="values = null"
          aria-label="关闭"
        >
          ×</button
        ><span class="eyebrow">RESPONSES / v{{ version }}</span>
        <h2>{{ valueQ.title }}</h2>
        <p class="muted">共 {{ values.total }} 条回答，每页 20 条</p>
        <div class="value-row" v-for="row in values.items">
          <p>{{ row.value }}</p>
          <small
            >{{ row.anonymous ? "匿名回答" : "实名回答" }} ·
            {{ dateLabel(row.submitted_at) }}</small
          >
        </div>
        <p v-if="!values.items.length" class="muted">暂无回答。</p>
        <div class="pagination">
          <button
            class="button"
            :disabled="page === 1"
            @click="showValues(valueQ, page - 1)"
          >
            上一页</button
          ><span
            >{{ page }} / {{ Math.max(1, Math.ceil(values.total / 20)) }}</span
          ><button
            class="button"
            :disabled="page * 20 >= values.total"
            @click="showValues(valueQ, page + 1)"
          >
            下一页
          </button>
        </div>
      </section>
    </div>
  </main>
</template>
