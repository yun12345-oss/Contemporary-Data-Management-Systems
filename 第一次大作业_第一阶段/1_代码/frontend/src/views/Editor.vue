<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useRoute, onBeforeRouteLeave } from "vue-router";
import { useSurveyEditor } from "../composables/useSurveyEditor";
import { parseRouting } from "../routing-validation";
import { type Question, typeNames, makeQuestion, makeId } from "../types";
import RoutingEditor from "../components/RoutingEditor.vue";
import QuestionInput from "../components/QuestionInput.vue";
const route = useRoute();
const sid = String(route.params.id);
const {
  survey,
  deadline,
  dirty,
  deadlineDirty,
  pendingChanges,
  busy,
  operation,
  error,
  message,
  statusText,
  load,
  save,
  publish,
  close,
  canLeave,
  unload,
} = useSurveyEditor(sid);
const selected = ref(0),
  preview = ref(false),
  jsonOpen = ref(false),
  jsonText = ref(""),
  jsonError = ref(""),
  jsonQuestionId = ref(""),
  closeConfirm = ref(false);
const question = computed(() => survey.value?.draft.questions[selected.value]);
async function confirmClose() {
  closeConfirm.value = false;
  await close();
}
function add(type: string) {
  if (!survey.value || survey.value.draft.questions.length >= 100) return;
  survey.value.draft.questions.push(makeQuestion(type));
  selected.value = survey.value.draft.questions.length - 1;
}
function remove(index: number) {
  if (!confirm("删除题目后，请检查其他题目是否有规则引用它。")) return;
  survey.value!.draft.questions.splice(index, 1);
  selected.value = Math.max(
    0,
    Math.min(selected.value, survey.value!.draft.questions.length - 1),
  );
}
function move(index: number, delta: number) {
  const qs = survey.value!.draft.questions;
  const to = index + delta;
  if (to < 0 || to >= qs.length) return;
  [qs[index], qs[to]] = [qs[to], qs[index]];
  selected.value = to;
}
function setValidation(q: Question, key: string, event: Event) {
  const value = (event.target as HTMLInputElement).value;
  if (value === "") delete q.validation[key];
  else q.validation[key] = Number(value);
}
function openJson() {
  jsonQuestionId.value = question.value!.id;
  jsonText.value = JSON.stringify(question.value!.routing, null, 2);
  jsonError.value = "";
  jsonOpen.value = true;
}
function applyJson() {
  try {
    const index = survey.value!.draft.questions.findIndex(
      (q) => q.id === jsonQuestionId.value,
    );
    if (index < 0) throw new Error("正在编辑的题目已不存在");
    const parsed = parseRouting(
      jsonText.value,
      survey.value!.draft.questions,
      index,
    );
    survey.value!.draft.questions[index].routing = parsed;
    jsonOpen.value = false;
  } catch (e: any) {
    jsonError.value = e.message + "；配置未应用";
  }
}
async function copy() {
  try {
    await navigator.clipboard.writeText(
      `${location.origin}/survey/${survey.value!.share_code}`,
    );
    message.value = "填写链接已复制";
  } catch {
    message.value = `${location.origin}/survey/${survey.value!.share_code}`;
  }
}
onMounted(() => {
  load();
  window.addEventListener("beforeunload", unload);
});
onBeforeUnmount(() => window.removeEventListener("beforeunload", unload));
onBeforeRouteLeave(canLeave);
</script>
<template>
  <main class="page editor-page">
    <div class="alert error" v-if="error" role="alert">{{ error }}</div>
    <div class="alert success" v-if="message" role="status">{{ message }}</div>
    <p v-if="busy" class="alert" role="status">
      正在处理本次操作。可以继续编辑，新修改会保留；请等待完成后再离开。
    </p>
    <template v-if="survey"
      ><div class="editor-header">
        <div>
          <router-link class="breadcrumb" to="/">← 我的问卷</router-link>
          <h1>
            设计你的问卷<span class="version-pill">{{
              survey.current_version
                ? "已发布 v" + survey.current_version
                : "尚未发布"
            }}</span>
          </h1>
          <p class="muted">{{ statusText }} · 编辑不会改变已发布版本</p>
        </div>
        <div class="actions">
          <button class="button" @click="preview = true">预览</button
          ><button class="button" :disabled="busy" @click="save">
            保存草稿</button
          ><button class="button primary" :disabled="busy" @click="publish">
            发布新版本 ↗
          </button>
        </div>
      </div>
      <div class="editor-layout">
        <aside class="editor-sidebar">
          <span class="eyebrow">QUESTION TYPES</span>
          <h3>添加题目</h3>
          <div class="type-buttons">
            <button
              v-for="(label, type) in typeNames"
              @click="add(String(type))"
              :disabled="survey.draft.questions.length >= 100"
            >
              <span>{{
                type === "single_choice"
                  ? "◉"
                  : type === "multiple_choice"
                    ? "☑"
                    : type === "text"
                      ? "T"
                      : "#"
              }}</span
              >{{ label }}<b>＋</b>
            </button>
          </div>
          <div class="sidebar-divider"></div>
          <h3>
            题目目录 <small>{{ survey.draft.questions.length }} / 100</small>
          </h3>
          <select
            class="mobile-question-select"
            v-model="selected"
            aria-label="选择编辑题目"
          >
            <option v-for="(q, i) in survey.draft.questions" :value="i">
              {{ i + 1 }}. {{ q.title || "未命名题目" }}
            </option></select
          ><button
            class="question-nav"
            v-for="(q, i) in survey.draft.questions"
            :key="q.id"
            :class="{ active: selected === i }"
            @click="selected = i"
          >
            <span>{{ String(i + 1).padStart(2, "0") }}</span
            >{{ q.title || "未命名题目" }}
          </button>
          <p class="input-hint" v-if="!survey.draft.questions.length">
            点击上方题型，添加第一道题。
          </p>
        </aside>
        <section class="editor-main">
          <div class="panel survey-basics">
            <span class="eyebrow">SURVEY DETAILS</span
            ><input
              class="survey-title-input"
              v-model="survey.draft.title"
              maxlength="200"
              aria-label="问卷标题"
              placeholder="填写问卷标题"
            /><textarea
              v-model="survey.draft.description"
              maxlength="5000"
              rows="2"
              aria-label="问卷说明"
              placeholder="写一段说明，告诉填写者这份问卷的目的…"
            ></textarea>
          </div>
          <div class="panel question-editor" v-if="question">
            <div class="question-editor-top">
              <span class="badge"
                >第 {{ selected + 1 }} 题 · {{ typeNames[question.type] }}</span
              >
              <div class="actions">
                <button
                  class="icon-button"
                  :disabled="selected === 0"
                  @click="move(selected, -1)"
                  title="上移"
                  aria-label="上移"
                >
                  ↑</button
                ><button
                  class="icon-button"
                  :disabled="selected === survey.draft.questions.length - 1"
                  @click="move(selected, 1)"
                  title="下移"
                  aria-label="下移"
                >
                  ↓</button
                ><button
                  class="icon-button danger-text"
                  @click="remove(selected)"
                  aria-label="删除题目"
                  title="删除题目"
                >
                  ×
                </button>
              </div>
            </div>
            <label
              >题目标题<input
                v-model="question.title"
                maxlength="500"
                placeholder="你想了解什么？" /></label
            ><label class="checkbox-label"
              ><input
                type="checkbox"
                v-model="question.required"
              />设为必答题</label
            >
            <div
              v-if="
                ['single_choice', 'multiple_choice'].includes(question.type)
              "
              class="options-editor"
            >
              <label>选项设置</label>
              <div
                v-for="(o, oi) in question.options"
                :key="o.id"
                class="option-edit"
              >
                <span>{{ String.fromCharCode(65 + oi) }}</span
                ><input
                  v-model="o.label"
                  maxlength="200"
                  :aria-label="'选项 ' + (oi + 1)"
                /><button
                  class="icon-button"
                  @click="question.options.splice(oi, 1)"
                  :disabled="question.options.length <= 2"
                  aria-label="删除选项"
                >
                  ×
                </button>
              </div>
              <button
                class="text-button"
                @click="
                  question.options.push({ id: makeId('o'), label: '新选项' })
                "
                :disabled="question.options.length >= 100"
              >
                ＋ 添加选项
              </button>
            </div>
            <div
              class="validation-grid"
              v-if="question.type === 'multiple_choice'"
            >
              <label
                >最少选择<input
                  type="number"
                  min="0"
                  :value="question.validation.min_choices ?? ''"
                  @input="setValidation(question, 'min_choices', $event)"
                  placeholder="不限制" /></label
              ><label
                >最多选择<input
                  type="number"
                  min="0"
                  :value="question.validation.max_choices ?? ''"
                  @input="setValidation(question, 'max_choices', $event)"
                  placeholder="选项总数"
              /></label>
            </div>
            <div class="validation-grid" v-if="question.type === 'text'">
              <label
                >最少字符数<input
                  type="number"
                  min="0"
                  :value="question.validation.min_length ?? ''"
                  @input="setValidation(question, 'min_length', $event)"
                  placeholder="0" /></label
              ><label
                >最多字符数<input
                  type="number"
                  min="0"
                  :value="question.validation.max_length ?? ''"
                  @input="setValidation(question, 'max_length', $event)"
                  placeholder="10000"
              /></label>
            </div>
            <div v-if="question.type === 'number'">
              <div class="validation-grid">
                <label
                  >最小值<input
                    type="number"
                    :value="question.validation.min ?? ''"
                    @input="setValidation(question, 'min', $event)"
                    placeholder="不限制" /></label
                ><label
                  >最大值<input
                    type="number"
                    :value="question.validation.max ?? ''"
                    @input="setValidation(question, 'max', $event)"
                    placeholder="不限制"
                /></label>
              </div>
              <label class="checkbox-label"
                ><input
                  type="checkbox"
                  v-model="question.validation.integer_only"
                />仅允许整数</label
              >
            </div>
            <RoutingEditor
              :question="question"
              :questions="survey.draft.questions"
              :index="selected"
            /><button class="text-button advanced-button" @click="openJson">
              高级：编辑组合条件 JSON
            </button>
            <p class="input-hint">
              题目 ID：{{ question.id }} ·
              调整含义或单位时，建议新建题目，保持历史数据语义。
            </p>
          </div>
          <div v-else class="panel empty-state">
            <span class="empty-symbol">＋</span>
            <h2>从第一个问题开始</h2>
            <p>在左侧选择题型，构建你的问卷。</p>
          </div>
        </section>
        <aside class="settings-sidebar panel">
          <span class="eyebrow">PUBLISH SETTINGS</span>
          <h3>填写与发布</h3>
          <label class="checkbox-label"
            ><input
              type="checkbox"
              v-model="survey.draft.allow_anonymous"
            />允许匿名提交</label
          >
          <p class="input-hint">填写者仍需登录，匿名时不向创建者展示身份。</p>
          <label class="checkbox-label"
            ><input
              type="checkbox"
              v-model="survey.draft.allow_repeat"
            />允许重复填写</label
          >
          <p class="input-hint">关闭时，同一账号在这份问卷中只能提交一次。</p>
          <label
            >截止时间<input type="datetime-local" v-model="deadline"
          /></label>
          <p class="input-hint">
            截止时间在发布时生效；留空表示不限制。保存草稿不会保存截止时间。
          </p>
          <p v-if="deadlineDirty" class="field-error" role="status">
            截止时间尚未发布，离开页面将丢失此项本地修改。
          </p>
          <template v-if="survey.current_version"
            ><div class="sidebar-divider"></div>
            <h3>已发布问卷</h3>
            <button class="button full" @click="copy">复制填写链接 ↗</button
            ><router-link
              class="button full"
              :to="`/survey/${survey.share_code}`"
              >打开填写页</router-link
            ><router-link
              class="button full"
              :to="`/surveys/${survey._id}/statistics`"
              >查看统计</router-link
            ><button
              class="text-button danger-text"
              v-if="survey.status === 'published'"
              @click="closeConfirm = true"
              :disabled="busy"
            >
              关闭问卷
            </button></template
          >
        </aside>
      </div>
      <div
        class="modal-backdrop"
        v-if="closeConfirm"
        @click.self="closeConfirm = false"
        @keydown.esc="closeConfirm = false"
      >
        <section
          class="modal"
          role="dialog"
          aria-modal="true"
          aria-label="关闭问卷确认"
        >
          <h2>关闭问卷</h2>
          <p>
            {{
              dirty
                ? "将先保存当前草稿，保存失败时不会关闭问卷。"
                : "关闭后将停止接收提交，已有答案和发布版本保留。"
            }}
          </p>
          <p v-if="deadlineDirty" class="field-error">
            截止时间尚未发布。关闭不会使其生效，此项修改仍保留在本页，离开前会提醒。
          </p>
          <div class="actions">
            <button class="button" @click="closeConfirm = false">取消</button
            ><button
              class="button primary"
              :disabled="busy"
              @click="confirmClose"
            >
              {{ dirty ? "保存草稿并关闭" : "确认关闭" }}
            </button>
          </div>
        </section>
      </div>
      <div class="modal-backdrop" v-if="preview" @click.self="preview = false">
        <section
          class="modal preview-modal"
          role="dialog"
          aria-modal="true"
          aria-label="问卷预览"
        >
          <button
            class="modal-close icon-button"
            @click="preview = false"
            aria-label="关闭预览"
          >
            ×</button
          ><span class="eyebrow">DRAFT PREVIEW</span>
          <h2>{{ survey.draft.title }}</h2>
          <p class="muted">{{ survey.draft.description }}</p>
          <div class="alert">
            此预览展示全部题目。实际跳转请发布后在填写页体验。
          </div>
          <div
            v-for="(q, i) in survey.draft.questions"
            class="preview-question"
          >
            <h3>
              {{ i + 1 }}. {{ q.title || "未命名题目" }}
              <span class="required" v-if="q.required">*</span>
            </h3>
            <QuestionInput :question="q" :model-value="null" />
          </div>
        </section>
      </div>
      <div
        class="modal-backdrop"
        v-if="jsonOpen"
        @click.self="jsonOpen = false"
      >
        <section
          class="modal"
          role="dialog"
          aria-modal="true"
          aria-label="编辑组合条件"
        >
          <h2>高级跳转配置</h2>
          <p class="muted">
            支持 all / any
            组合；应用前检查结构、引用、类型和跳转目标，发布时后端再次检查。
          </p>
          <textarea
            class="code-input"
            v-model="jsonText"
            rows="18"
            aria-label="跳转规则 JSON"
          ></textarea>
          <p class="field-error" v-if="jsonError">{{ jsonError }}</p>
          <div class="actions">
            <button class="button" @click="jsonOpen = false">取消</button
            ><button class="button primary" @click="applyJson">应用配置</button>
          </div>
        </section>
      </div>
    </template>
    <div v-else-if="!error" class="empty-state">正在加载编辑器…</div>
  </main>
</template>
