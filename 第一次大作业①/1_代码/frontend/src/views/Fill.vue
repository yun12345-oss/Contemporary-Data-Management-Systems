<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useRoute, onBeforeRouteLeave } from "vue-router";
import { api, auth, ApiError } from "../api";
import { typeNames, dateLabel } from "../types";
import { validate } from "../rules";
import { draftPath, answerValue, pruneSkipped } from "../attempt-progress";
import { useAttempt } from "../composables/useAttempt";
import { pendingWork } from "../pending-work";
import QuestionInput from "../components/QuestionInput.vue";
const route = useRoute();
const {
  attempt,
  answers,
  currentId,
  dirty,
  saving,
  paused,
  message,
  error,
  restore,
  changed,
  flush,
  reload,
  reauthenticate,
  cancelTimers,
} = useAttempt();
const info = ref<any>(null),
  resume = ref<any>(null),
  anonymous = ref(false);
const fieldError = ref(""),
  busy = ref(false),
  receipt = ref<any>(null);
const loginName = ref(auth.user?.username || ""),
  loginPassword = ref("");
const path = computed(() =>
  attempt.value ? draftPath(attempt.value.definition, answers.value) : [],
);
const cursor = computed(() =>
  Math.max(
    0,
    path.value.findIndex((q) => q.id === currentId.value),
  ),
);
const current = computed(() => path.value[cursor.value]);
let departing = false;
function displayAnswer(q: any, value: any) {
  const label = (id: any) =>
    q.options.find((o: any) => o.id === id)?.label || id;
  return Array.isArray(value)
    ? value.map(label).join("、")
    : q.type === "single_choice"
      ? label(value)
      : value;
}
async function load() {
  error.value = "";
  try {
    resume.value = await api(`/public/${route.params.share}/attempt`);
    if (!resume.value) info.value = await api(`/public/${route.params.share}`);
  } catch (e: any) {
    error.value = e.message;
  }
}
function continueAttempt() {
  restore(resume.value);
  resume.value = null;
}
async function restart() {
  attempt.value = null;
  receipt.value = null;
  anonymous.value = false;
  await load();
}
async function discardResume() {
  if (!confirm("放弃后会立即删除这份草稿的答案，无法恢复。确认放弃？")) return;
  busy.value = true;
  try {
    await api(`/attempts/${resume.value._id}/abandon`, "POST", {
      revision: resume.value.revision,
    });
    resume.value = null;
    await load();
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
async function start() {
  busy.value = true;
  error.value = "";
  try {
    restore(
      await api(`/public/${route.params.share}/attempt`, "POST", {
        anonymous: anonymous.value,
      }),
    );
    receipt.value = null;
  } catch (e: any) {
    error.value = e.message;
  } finally {
    busy.value = false;
  }
}
function change(value: any) {
  if (!current.value || busy.value || attempt.value.read_only) return;
  answers.value[current.value.id] = value;
  fieldError.value = "";
  // 仅当当前题合法时清理确定失效的旧路径；不因中间输入删除后续暂存内容。
  pruneSkipped(attempt.value.definition, answers.value);
  changed();
}
async function previous() {
  if (cursor.value === 0 || busy.value) return;
  currentId.value = path.value[cursor.value - 1].id;
  fieldError.value = "";
  if (!attempt.value.read_only) {
    changed();
    await flush();
  }
}
async function next() {
  if (!current.value || busy.value) return;
  if (!attempt.value.read_only) {
    fieldError.value = validate(
      current.value,
      answerValue(current.value, answers.value[current.value.id]),
    );
    if (fieldError.value) return;
  }
  if (cursor.value < path.value.length - 1) {
    currentId.value = path.value[cursor.value + 1].id;
    fieldError.value = "";
    if (!attempt.value.read_only) {
      changed();
      await flush();
    }
    return;
  }
  if (attempt.value.read_only) return;
  busy.value = true;
  error.value = "";
  cancelTimers();
  try {
    if (!(await flush())) return;
    receipt.value = await api(`/attempts/${attempt.value._id}/submit`, "POST", {
      revision: attempt.value.revision,
    });
    attempt.value.status = "submitted";
    answers.value = {};
    info.value = { allow_repeat: attempt.value.definition.allow_repeat };
  } catch (e: any) {
    error.value = e.message;
    if (e instanceof ApiError && e.status === 401) paused.value = "auth";
    if (e instanceof ApiError && e.status === 409) paused.value = "conflict";
    if (e.details) {
      const first = path.value.find((q) => e.details[q.id]);
      if (first) {
        currentId.value = first.id;
        fieldError.value = e.details[first.id];
      }
    }
  } finally {
    busy.value = false;
  }
}
async function loginAgain() {
  busy.value = true;
  try {
    await reauthenticate(loginName.value, loginPassword.value);
  } finally {
    loginPassword.value = "";
    busy.value = false;
  }
}
async function leave() {
  if (busy.value) return false;
  if (departing || !attempt.value || receipt.value || attempt.value.read_only)
    return true;
  if (await flush()) return true;
  departing = confirm(
    "部分输入尚未保存。离开会丢失未同步部分，已保存内容仍可恢复。确认离开？",
  );
  return departing;
}
function unload(e: BeforeUnloadEvent) {
  if (dirty.value && !receipt.value && !attempt.value?.read_only) {
    e.preventDefault();
    e.returnValue = "";
  }
}
function hidden() {
  if (document.visibilityState === "hidden" && !paused.value) void flush();
}
onMounted(() => {
  load();
  pendingWork.beforeLogout = leave;
  window.addEventListener("beforeunload", unload);
  document.addEventListener("visibilitychange", hidden);
});
onBeforeUnmount(() => {
  pendingWork.beforeLogout = null;
  window.removeEventListener("beforeunload", unload);
  document.removeEventListener("visibilitychange", hidden);
});
onBeforeRouteLeave(leave);
</script>
<template>
  <main class="fill-page">
    <div class="fill-topline">
      <span class="eyebrow">A LITTLE THOUGHT. A BIG DIFFERENCE.</span
      ><span>问序 / 问卷填写</span>
    </div>
    <div class="alert error" v-if="error" role="alert">{{ error }}</div>
    <section class="fill-card" v-if="receipt">
      <span class="success-symbol">✓</span
      ><span class="eyebrow">RESPONSE RECEIVED</span>
      <h1>感谢你的认真回答。</h1>
      <p class="muted">你的反馈已成功保存，每一份回答都让理解更进一步。</p>
      <div class="receipt">
        <span>提交版本 v{{ receipt.version }}</span
        ><span>{{ dateLabel(receipt.submitted_at) }}</span>
      </div>
      <button class="button primary" v-if="info?.allow_repeat" @click="restart">
        再填写一次</button
      ><router-link class="button" to="/">返回工作台</router-link>
    </section>
    <section class="fill-card" v-else-if="resume && !attempt">
      <span class="eyebrow">CONTINUE YOUR RESPONSE</span>
      <h1>{{ resume.definition.title }}</h1>
      <p>找到一份未完成填写，保存于 {{ dateLabel(resume.updated_at) }}。</p>
      <p class="muted">
        {{ resume.anonymous ? "匿名填写" : "实名填写" }} · v{{
          resume.version
        }}，恢复时保留原选择及版本。
      </p>
      <p v-if="resume.read_only" class="alert">
        {{ resume.read_only_reason }}，可查看已保存内容。
      </p>
      <button class="button primary" @click="continueAttempt">
        {{ resume.read_only ? "查看已保存内容" : "继续填写" }}
      </button>
      <button class="button" :disabled="busy" @click="discardResume">
        放弃草稿
      </button>
    </section>
    <section class="fill-card" v-else-if="info && !attempt">
      <span class="eyebrow">YOU ARE INVITED</span>
      <h1>{{ info.title }}</h1>
      <p class="survey-description">
        {{ info.description || "感谢你抽出时间，分享真实的想法。" }}
      </p>
      <div class="fill-facts">
        <span>{{ info.question_count }} 道题目</span
        ><span>版本 v{{ info.version }}</span
        ><span>{{
          info.deadline ? "截止 " + dateLabel(info.deadline) : "不限截止时间"
        }}</span>
      </div>
      <label class="answer-option" v-if="info.allow_anonymous"
        ><input type="checkbox" v-model="anonymous" /><span
          >匿名提交 <small>不向问卷创建者展示账号身份</small></span
        ></label
      >
      <p class="input-hint">
        {{
          info.allow_repeat ? "本问卷允许重复填写。" : "每个账号仅能提交一次。"
        }}填写过程会自动保存，登录同一账号可继续填写。匿名选择在开始后固定；未提交内容不计入统计。
      </p>
      <button class="button primary" :disabled="busy" @click="start">
        开始填写 →
      </button>
    </section>
    <template v-else-if="attempt && current"
      ><div class="fill-progress">
        <span>{{ attempt.definition.title }}</span
        ><span>{{ cursor + 1 }} / {{ path.length }} 题 · 路径随回答变化</span>
        <div>
          <i :style="{ width: ((cursor + 1) / path.length) * 100 + '%' }"></i>
        </div>
      </div>
      <section class="fill-card answering" :key="current.id">
        <div class="attempt-save-status" role="status" aria-live="polite">
          {{ saving ? "正在保存…" : dirty ? "当前修改尚未保存" : message }}
          <button
            class="text-button"
            v-if="dirty && !paused"
            :disabled="saving || busy"
            @click="flush"
          >
            立即保存
          </button>
        </div>
        <p v-if="attempt.read_only" class="alert">
          {{ attempt.read_only_reason }}。已保存内容仅供查看。
        </p>
        <details v-if="attempt.read_only">
          <summary>查看全部已保存输入</summary>
          <div
            v-for="q in attempt.definition.questions.filter((q: any) =>
              Object.hasOwn(answers, q.id),
            )"
            :key="q.id"
          >
            <strong>{{ q.title }}</strong>
            <p>{{ displayAnswer(q, answers[q.id]) }}</p>
          </div>
        </details>
        <p v-if="paused === 'conflict'" class="alert">
          服务器草稿已变化或问卷已关闭，当前输入保留。<button
            class="text-button"
            @click="reload"
          >
            重新加载草稿
          </button>
        </p>
        <fieldset
          :disabled="busy || attempt.read_only || paused === 'conflict'"
          class="answer-fieldset"
        >
          <span class="eyebrow"
            >QUESTION {{ String(cursor + 1).padStart(2, "0") }} /
            {{ typeNames[current.type] }}</span
          >
          <h1>
            {{ current.title }}
            <span class="required" v-if="current.required">*</span>
          </h1>
          <QuestionInput
            :question="current"
            :model-value="answers[current.id]"
            @update:model-value="change"
            :error="fieldError"
          />
        </fieldset>
        <div class="fill-navigation">
          <button
            class="button"
            :disabled="cursor === 0 || busy"
            @click="previous()"
          >
            ← 上一题</button
          ><span class="input-hint"
            >{{ attempt.anonymous ? "匿名填写" : "实名填写" }} · v{{
              attempt.version
            }}</span
          ><button
            class="button primary"
            :disabled="
              busy ||
              (attempt.read_only && cursor === path.length - 1) ||
              (!!paused && !attempt.read_only)
            "
            @click="next"
          >
            {{
              busy
                ? "正在提交…"
                : cursor === path.length - 1
                  ? "提交回答 ✓"
                  : "下一题 →"
            }}
          </button>
        </div>
      </section>
      <p class="fill-footnote">
        返回修改答案可能改变后续路径，失效路径上的回答会被清除。
      </p></template
    >
    <div v-else-if="!error" class="empty-state">正在准备问卷…</div>
    <section class="fill-card" v-if="paused === 'auth'">
      <h2>重新登录并保存</h2>
      <p>
        保持本页打开，使用 {{ auth.user?.username }} 重新登录，输入不会被清空。
      </p>
      <form @submit.prevent="loginAgain">
        <label>账号<input v-model="loginName" autocomplete="username" /></label>
        <label
          >密码<input
            v-model="loginPassword"
            type="password"
            autocomplete="current-password"
        /></label>
        <button class="button primary" :disabled="busy">登录并继续保存</button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.answer-fieldset {
  border: 0;
  padding: 0;
  margin: 1rem 0;
  min-width: 0;
}
.attempt-save-status {
  color: var(--muted, #52665c);
  font-size: 0.9rem;
  margin-bottom: 1rem;
}
</style>
