<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
const route = useRoute();
const vid = String(route.params.id),
  data = ref<any>(null),
  start = ref(""),
  end = ref(""),
  bins = ref("0,18,30,45,60,121"),
  sid = ref(
    typeof route.query.survey_id === "string" ? route.query.survey_id : "",
  ),
  busy = ref(false),
  error = ref("");
async function load() {
  busy.value = true;
  error.value = "";
  try {
    const p = new URLSearchParams();
    if (start.value) p.set("start", new Date(start.value).toISOString());
    if (end.value) p.set("end", new Date(end.value).toISOString());
    if (sid.value) p.set("survey_id", sid.value);
    for (const b of bins.value.split(",")) p.append("boundaries", b.trim());
    data.value = await api(`/question-versions/${vid}/statistics?${p}`);
  } catch (e: any) {
    data.value = null;
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
onMounted(load);
</script>
<template>
  <main class="page">
    <router-link to="/questions">← 题目管理</router-link>
    <h1>单题跨问卷统计</h1>
    <p class="muted">
      仅汇总同一确定版本、自有或获得有效汇总统计授权的问卷；时间按正式提交时间筛选。不同版本不自动合并。
    </p>
    <form class="panel phase2-card" @submit.prevent="load">
      <div class="stats-filters">
        <label>开始时间<input type="datetime-local" v-model="start" /></label
        ><label>结束时间<input type="datetime-local" v-model="end" /></label
        ><label>限定问卷ID（可留空）<input v-model="sid" /></label
        ><label>数字分组边界（逗号分隔）<input v-model="bins" /></label
        ><button class="button primary" :disabled="busy">
          {{ busy ? "统计中…" : "筛选" }}
        </button>
      </div>
    </form>
    <p v-if="error" class="alert error">{{ error }}</p>
    <template v-if="data"
      ><h2>{{ data.content.title }} · v{{ data.version }}</h2>
      <div class="stats-summary panel">
        <div>
          <strong>{{ data.coverage_surveys }}</strong
          ><span>统计覆盖问卷（含零作答）</span>
        </div>
        <div>
          <strong>{{ data.answered_surveys }}</strong
          ><span>有有效作答的问卷</span>
        </div>
        <div>
          <strong>{{ data.valid_responses }}</strong
          ><span>有效答卷</span>
        </div>
        <div>
          <strong>{{ data.valid_answers }}</strong
          ><span>有效作答条数</span>
        </div>
      </div>
      <p class="input-hint">
        {{ data.notice }}
        覆盖数按有权范围内曾发布该版本的问卷去重，包含当前时间范围零作答的问卷；使用总量请在使用追踪查看，这里不展示跨问卷去重人数。
      </p>
      <section class="panel phase2-card" v-if="data.options">
        <h2>选项分布</h2>
        <p class="input-hint">比例分母为有效作答条数；多选合计可超过100%。</p>
        <div class="phase2-picker-row" v-for="o in data.options">
          <strong>{{ o.label }}</strong
          ><span>{{ o.count }} 次 · {{ (o.ratio * 100).toFixed(1) }}%</span
          ><progress :value="o.ratio" max="1" />
        </div>
      </section>
      <section class="panel phase2-card" v-if="data.distribution">
        <h2>数值分布</h2>
        <p>
          平均值：{{ data.average ?? "暂无" }} · 最小值：{{
            data.min ?? "暂无"
          }}
          · 最大值：{{ data.max ?? "暂无" }}
        </p>
        <div class="phase2-picker-row" v-for="b in data.distribution">
          <strong>{{ b.label || `[${b.lower}, ${b.upper})` }}</strong
          ><span>{{ b.count }} 条</span
          ><progress :value="b.count" :max="data.valid_answers || 1" />
        </div>
      </section>
      <p v-if="data.content.type === 'text'" class="panel">
        文本仅提供汇总条数。明细请在有权访问的原问卷统计中查看。
      </p></template
    >
  </main>
</template>
