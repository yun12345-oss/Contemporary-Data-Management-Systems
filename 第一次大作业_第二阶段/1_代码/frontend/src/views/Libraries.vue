<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { api } from "../api";
import QuestionPicker from "../components/QuestionPicker.vue";
const libs = ref<any[]>([]),
  data = ref<any>(null),
  name = ref(""),
  description = ref(""),
  error = ref(""),
  busy = ref(false),
  picker = ref(false),
  page = ref(1),
  listPage = ref(1),
  listTotal = ref(0),
  editItem = ref<any>(null);
async function load() {
  try {
    const r = await api(`/libraries?page=${listPage.value}`);
    libs.value = r.items;
    listTotal.value = r.total;
  } catch (e: any) {
    error.value = e.message;
  }
}
let selectionSequence = 0;
let disposed = false;
function closePicker() {
  picker.value = false;
  editItem.value = null;
}
async function select(id: string) {
  closePicker();
  const seq = ++selectionSequence;
  error.value = "";
  try {
    const result = await api(`/libraries/${id}/items?page=${page.value}`);
    if (!disposed && seq === selectionSequence) data.value = result;
  } catch (e: any) {
    if (!disposed && seq === selectionSequence) error.value = e.message;
  }
}
function chooseLibrary(id: string) {
  if (busy.value) return;
  page.value = 1;
  data.value = null;
  return select(id);
}
async function create() {
  busy.value = true;
  try {
    const l = await api("/libraries", "POST", {
      name: name.value,
      description: description.value,
    });
    name.value = "";
    description.value = "";
    await load();
    page.value = 1;
    await select(l._id);
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
async function rename() {
  const newName = prompt("题库名称", data.value.library.name);
  if (newName === null) return;
  busy.value = true;
  try {
    await api(`/libraries/${data.value.library._id}`, "PUT", {
      name: newName,
      description: data.value.library.description,
      revision: data.value.library.revision,
    });
    await load();
    await select(data.value.library._id);
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
async function pick(vid: string) {
  if (busy.value || !picker.value || !data.value) return;
  const target = {
    libraryId: data.value.library._id,
    revision: data.value.library.revision,
    memberId: editItem.value?._id,
    position: editItem.value?.position ?? data.value.total,
  };
  busy.value = true;
  try {
    const lid = target.libraryId;
    await api(
      `/libraries/${lid}/items${target.memberId ? "/" + target.memberId : ""}`,
      target.memberId ? "PUT" : "POST",
      {
        revision: target.revision,
        question_version_id: vid,
        position: target.position,
      },
    );
    picker.value = false;
    editItem.value = null;
    await select(lid);
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
async function position(item: any) {
  const input = prompt("排序值（较小的排前面）", String(item.position));
  if (input === null) return;
  const p = Number(input);
  if (!Number.isInteger(p) || p < 0 || p > 100000) {
    error.value = "排序值需为0～100000的整数";
    return;
  }
  busy.value = true;
  try {
    await api(`/libraries/${data.value.library._id}/items/${item._id}`, "PUT", {
      revision: data.value.library.revision,
      question_version_id: item.question_version_id,
      position: p,
    });
    await select(data.value.library._id);
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
async function remove(item: any) {
  if (!confirm("仅从题库移除，不删除题目版本或问卷实例。继续？")) return;
  busy.value = true;
  try {
    await api(
      `/libraries/${data.value.library._id}/items/${item._id}/remove`,
      "POST",
      { revision: data.value.library.revision },
    );
    await select(data.value.library._id);
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
onMounted(load);
onBeforeUnmount(() => {
  disposed = true;
  selectionSequence++;
  closePicker();
});
</script>
<template>
  <main class="page">
    <h1>我的题库</h1>
    <p class="muted">
      同一题目可收录多个确定版本。题库更新不影响已经导入问卷的实例。
    </p>
    <p class="alert error" v-if="error">{{ error }}</p>
    <form class="panel phase2-card" @submit.prevent="create">
      <div class="actions">
        <input
          v-model="name"
          required
          maxlength="200"
          placeholder="新题库名称"
        /><input
          v-model="description"
          maxlength="2000"
          placeholder="题库说明"
        /><button class="button primary" :disabled="busy">创建题库</button>
      </div>
    </form>
    <div class="actions phase2-card">
      <button
        class="button"
        v-for="l in libs"
        :disabled="busy"
        @click="chooseLibrary(l._id)"
      >
        {{ l.name }}
      </button>
    </div>
    <div class="actions">
      <button
        class="button"
        :disabled="listPage <= 1"
        @click="
          listPage--;
          load();
        "
      >
        上一页题库</button
      ><button
        class="button"
        :disabled="listPage * 20 >= listTotal"
        @click="
          listPage++;
          load();
        "
      >
        下一页题库
      </button>
    </div>
    <section class="panel phase2-card" v-if="data">
      <div class="editor-header">
        <div>
          <h2>{{ data.library.name }}</h2>
          <p>{{ data.library.description }}</p>
        </div>
        <div class="actions">
          <button class="button" :disabled="busy" @click="rename">
            修改名称</button
          ><button
            class="button primary"
            :disabled="busy"
            @click="
              editItem = null;
              picker = !picker;
            "
          >
            加入题目
          </button>
        </div>
      </div>
      <QuestionPicker
        v-if="picker && !busy"
        :key="`${data.library._id}:${editItem?._id || 'new'}`"
        :question-id="editItem?.question_id"
        @pick="pick"
      />
      <div class="phase2-picker-row" v-for="item in data.items" :key="item._id">
        <strong
          >{{ item.version?.content.title || "当前无权读取此版本" }}
          <span v-if="item.version">v{{ item.version.version }}</span></strong
        ><span class="muted"
          >排序 {{ item.position
          }}{{ item.available ? "" : " · 不能新增使用" }}</span
        ><button
          class="button"
          :disabled="busy"
          @click="
            editItem = item;
            picker = true;
          "
        >
          更新版本</button
        ><button
          class="button"
          :disabled="busy || !item.available"
          @click="position(item)"
        >
          排序</button
        ><button class="button" :disabled="busy" @click="remove(item)">
          移除
        </button>
      </div>
      <div class="actions">
        <button
          class="button"
          :disabled="busy || page <= 1"
          @click="
            page--;
            select(data.library._id);
          "
        >
          上一页</button
        ><span>{{ page }} / {{ Math.max(1, Math.ceil(data.total / 20)) }}</span
        ><button
          class="button"
          :disabled="busy || page * 20 >= data.total"
          @click="
            page++;
            select(data.library._id);
          "
        >
          下一页
        </button>
      </div>
    </section>
  </main>
</template>
