<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
import { typeNames, dateLabel } from "../types";
import { optionCount, optionPercent, type CountBasis } from "../statistics";
const route = useRoute(),
  sid = String(route.params.id),
  versions = ref<any[]>([]),
  version = ref(0),
  summaryResult = ref<{ context: QueryContext; data: any } | null>(null),
  error = ref(""),
  busy = ref(false),
  selected = ref("all"),
  start = ref(""),
  end = ref(""),
  detailResult = ref<{
    context: QueryContext;
    question: any;
    page: number;
    data: any;
  } | null>(null),
  detailOpen = ref(false),
  detailBusy = ref(false),
  basis = ref<CountBasis>("responses");
type QueryContext = { version: number; start: string; end: string };
const stats = computed(() => summaryResult.value?.data);
const values = computed(() => detailResult.value?.data);
const valueQ = computed(() => detailResult.value?.question);
const page = computed(() => detailResult.value?.page ?? 1);
const appliedContext = computed(() => summaryResult.value?.context);
const unapplied = computed(
  () =>
    !!appliedContext.value &&
    (version.value !== appliedContext.value.version ||
      start.value !== appliedContext.value.start ||
      end.value !== appliedContext.value.end),
);
const shown = computed(
  () =>
    stats.value?.questions.filter(
      (q: any) => selected.value === "all" || q.id === selected.value,
    ) || [],
);
let summarySequence = 0,
  detailSequence = 0,
  disposed = false;
function query(c: QueryContext) {
  const p = new URLSearchParams({ version: String(c.version) });
  if (c.start) p.set("start", new Date(c.start).toISOString());
  if (c.end) p.set("end", new Date(c.end).toISOString());
  return p.toString();
}
function closeValues() {
  detailSequence++;
  detailOpen.value = false;
  detailBusy.value = false;
  detailResult.value = null;
}
async function load() {
  const seq = ++summarySequence;
  const context = {
    version: version.value,
    start: start.value,
    end: end.value,
  };
  closeValues();
  summaryResult.value = null;
  busy.value = true;
  error.value = "";
  try {
    const data = await api(`/surveys/${sid}/statistics?${query(context)}`);
    if (!disposed && seq === summarySequence)
      summaryResult.value = { context, data };
  } catch (e: any) {
    if (!disposed && seq === summarySequence) {
      error.value = e.message;
      summaryResult.value = null;
    }
  } finally {
    if (!disposed && seq === summarySequence) busy.value = false;
  }
}
async function showValues(q: any, p = 1) {
  if (!appliedContext.value) return;
  const context = { ...appliedContext.value };
  const seq = ++detailSequence;
  const summary = summarySequence;
  detailOpen.value = true;
  detailBusy.value = true;
  detailResult.value = null;
  error.value = "";
  try {
    const data = await api(
      `/surveys/${sid}/questions/${q.id}/values?${query(context)}&page=${p}`,
    );
    if (
      !disposed &&
      detailOpen.value &&
      seq === detailSequence &&
      summary === summarySequence
    )
      detailResult.value = { context, question: q, page: p, data };
  } catch (e: any) {
    if (!disposed && seq === detailSequence && summary === summarySequence) {
      error.value = e.message;
      closeValues();
    }
  } finally {
    if (!disposed && seq === detailSequence) detailBusy.value = false;
  }
}
onBeforeUnmount(() => {
  disposed = true;
  summarySequence++;
  closeValues();
});
onMounted(async () => {
  try {
    const result = await api(`/surveys/${sid}/versions`);
    if (disposed) return;
    versions.value = result;
    version.value = versions.value[0]?.version || 0;
    if (version.value) await load();
    else error.value = "发布问卷后即可查看统计";
  } catch (e: any) {
    if (!disposed) error.value = e.message;
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
    <p v-if="unapplied" role="status">
      筛选条件尚未应用，当前结果及明细仍采用已应用范围。
    </p>
    <p v-if="appliedContext" class="input-hint">
      统计范围：v{{ appliedContext.version }}；正式提交时间：{{
        appliedContext.start || "不限"
      }}
      至 {{ appliedContext.end || "不限" }}。
    </p>
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
    <div class="modal-backdrop" v-if="detailOpen" @click.self="closeValues">
      <section
        class="modal"
        role="dialog"
        aria-modal="true"
        aria-label="填写内容"
      >
        <button
          class="modal-close icon-button"
          @click="closeValues"
          aria-label="关闭"
        >
          ×
        </button>
        <p v-if="detailBusy">正在加载回答…</p>
        <template v-if="detailResult"
          ><span class="eyebrow"
            >RESPONSES / v{{ detailResult.context.version }}</span
          >
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
              >{{ page }} /
              {{ Math.max(1, Math.ceil(values.total / 20)) }}</span
            ><button
              class="button"
              :disabled="page * 20 >= values.total"
              @click="showValues(valueQ, page + 1)"
            >
              下一页
            </button>
          </div>
        </template>
      </section>
    </div>
  </main>
</template>
