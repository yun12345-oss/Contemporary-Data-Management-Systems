<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from "vue";
import { api } from "../api";
const props = defineProps<{ questionId?: string }>();
const emit = defineEmits<{ pick: [id: string] }>();
const items = ref<any[]>([]),
  libs = ref<any[]>([]),
  library = ref(""),
  search = ref(""),
  page = ref(1),
  total = ref(0),
  error = ref(""),
  busy = ref(false),
  libraryBusy = ref(false),
  libraryError = ref(""),
  libraryPage = ref(0),
  libraryTotal = ref(0);
let sequence = 0;
let disposed = false;
async function load() {
  const seq = ++sequence;
  items.value = [];
  total.value = 0;
  busy.value = true;
  error.value = "";
  try {
    const data = library.value
      ? await api(
          `/libraries/${library.value}/items?page=${page.value}&search=${encodeURIComponent(search.value)}${props.questionId ? "&question_id=" + encodeURIComponent(props.questionId) : ""}`,
        )
      : await api(
          `/questions?page=${page.value}&search=${encodeURIComponent(search.value)}${props.questionId ? "&question_id=" + encodeURIComponent(props.questionId) : ""}`,
        );
    if (seq !== sequence) return;
    items.value = library.value
      ? data.items
          .filter((i: any) => i.version)
          .map((i: any) => ({
            _id: i.question_id,
            picker_key: i._id,
            title: i.version.content.title,
            archived: !i.available,
            versions: [i.version],
          }))
      : data.items;
    total.value = data.total;
  } catch (e: any) {
    if (seq === sequence) {
      error.value = e.message;
      items.value = [];
      total.value = 0;
    }
  } finally {
    if (seq === sequence) busy.value = false;
  }
}
async function loadLibraries() {
  if (libraryBusy.value) return;
  libraryBusy.value = true;
  libraryError.value = "";
  try {
    const next = libraryPage.value + 1;
    const data = await api(
      next === 1 ? "/libraries" : `/libraries?page=${next}`,
    );
    if (disposed) return;
    const known = new Set(libs.value.map((l) => l._id));
    libs.value.push(...data.items.filter((l: any) => !known.has(l._id)));
    libraryTotal.value = data.total ?? libs.value.length;
    libraryPage.value = next;
  } catch (e: any) {
    if (!disposed) libraryError.value = e.message;
  } finally {
    if (!disposed) libraryBusy.value = false;
  }
}
watch(
  () => props.questionId,
  () => {
    page.value = 1;
    search.value = "";
    load();
  },
  { flush: "sync" },
);
onBeforeUnmount(() => {
  disposed = true;
  sequence++;
});
onMounted(async () => {
  await Promise.all([load(), loadLibraries()]);
});
</script>
<template>
  <section class="phase2-picker">
    <div class="actions">
      <input
        v-model="search"
        placeholder="搜索可用题目"
        aria-label="搜索题目"
        @keyup.enter="
          page = 1;
          load();
        "
      /><select
        v-model="library"
        @change="
          page = 1;
          load();
        "
        aria-label="选择题库"
      >
        <option value="">全部可用题目</option>
        <option v-for="l in libs" :value="l._id">{{ l.name }}</option></select
      ><button
        class="button"
        :disabled="busy"
        @click="
          page = 1;
          load();
        "
      >
        查询
      </button>
    </div>
    <button
      class="text-button"
      v-if="libs.length < libraryTotal"
      :disabled="libraryBusy"
      @click="loadLibraries"
    >
      {{ libraryBusy ? "加载中…" : "加载更多题库" }}
    </button>
    <p class="alert error" v-if="libraryError">
      题库列表加载失败：{{ libraryError }}
      <button
        class="text-button"
        :disabled="libraryBusy"
        @click="loadLibraries"
      >
        重试题库列表
      </button>
    </p>
    <p v-if="error" class="alert error">{{ error }}</p>
    <p v-if="busy">正在加载…</p>
    <div
      v-for="q in items.filter((q) => !questionId || q._id === questionId)"
      :key="q.picker_key || q._id"
      class="phase2-picker-row"
    >
      <strong>{{ q.title }}</strong
      ><span v-if="q.archived" class="muted">已归档或无当前使用权</span
      ><button
        class="button"
        v-for="v in q.versions"
        :key="v._id"
        :disabled="q.archived || busy"
        @click="emit('pick', v._id)"
      >
        选择 v{{ v.version }}
      </button>
    </div>
    <p v-if="!busy && !items.length" class="muted">
      {{
        questionId
          ? "该题目系列暂无可用的授权版本。可联系所有者授权，或移除此成员。"
          : "没有可选题目。先创建题目，或请所有者共享指定版本。"
      }}
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
      ><span>{{ page }} / {{ Math.max(1, Math.ceil(total / 20)) }}</span
      ><button
        class="button"
        :disabled="page * 20 >= total || busy"
        @click="
          page++;
          load();
        "
      >
        下一页
      </button>
    </div>
  </section>
</template>
