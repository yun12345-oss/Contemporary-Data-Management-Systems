<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "../api";
const props = defineProps<{ questionId: string }>();
const data = ref<any>(null),
  error = ref(""),
  page = ref(1);
async function load() {
  error.value = "";
  try {
    data.value = await api(
      `/questions/${props.questionId}/usage?page=${page.value}`,
    );
  } catch (e: any) {
    data.value = null;
    error.value = e.message;
  }
}
onMounted(load);
</script>
<template>
  <section>
    <h2>使用情况</h2>
    <p v-if="error" class="alert error">{{ error }}</p>
    <template v-if="data"
      ><p>
        {{ data.scope }} · 使用问卷 {{ data.used_surveys }} 份 · 当前草稿
        {{ data.draft_surveys }} · 当前发布
        {{ data.current_published_surveys }} · 历史发布
        {{ data.historical_published_surveys }}
      </p>
      <p class="input-hint">
        各分类按问卷去重，可能重叠；历史发布包含当前发布。仅展示自己的问卷明细；他人问卷仅计入题目所有者的脱敏汇总。
      </p>
      <div class="phase2-picker-row" v-for="s in data.items">
        <router-link :to="`/surveys/${s.survey_id}/edit`">{{
          s.title
        }}</router-link
        ><span
          >草稿：{{ s.draft ? "使用" : "未使用" }}；当前发布：{{
            s.current_published ? "使用" : "未使用"
          }}；发布版本：{{ s.published_versions.join("、") || "无" }}</span
        >
      </div>
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
        ><button
          class="button"
          :disabled="page * 20 >= data.detail_total"
          @click="
            page++;
            load();
          "
        >
          下一页
        </button>
      </div></template
    >
  </section>
</template>
