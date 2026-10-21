import { ref, computed, onBeforeUnmount } from "vue";
import { api, ApiError, auth } from "../api";

export function useAttempt() {
  const attempt = ref<any>(null),
    answers = ref<Record<string, any>>({});
  const currentId = ref<string | null>(null),
    baseline = ref("");
  const saving = ref(false),
    message = ref(""),
    error = ref("");
  const paused = ref<"" | "auth" | "conflict" | "closed">("");
  const snapshot = () =>
    JSON.stringify({
      answers: answers.value,
      current_question_id: currentId.value,
    });
  const dirty = computed(
    () => !!attempt.value && snapshot() !== baseline.value,
  );
  let timer: ReturnType<typeof setTimeout> | undefined;
  let maximum: ReturnType<typeof setTimeout> | undefined;
  let running: Promise<boolean> | null = null;
  let alive = true;
  function cancelTimers() {
    clearTimeout(timer);
    clearTimeout(maximum);
    timer = maximum = undefined;
  }
  function restore(doc: any) {
    cancelTimers();
    attempt.value = doc;
    answers.value = JSON.parse(JSON.stringify(doc.answers));
    currentId.value = doc.current_question_id;
    baseline.value = snapshot();
    paused.value = doc.read_only ? "closed" : "";
    message.value = doc.read_only
      ? doc.read_only_reason || "本次填写已结束"
      : "已恢复服务器保存的进度";
    error.value = "";
  }
  function changed() {
    if (
      !attempt.value ||
      attempt.value.read_only ||
      attempt.value.status !== "in_progress"
    )
      return;
    message.value = "有修改尚未保存";
    if (paused.value || !alive) return;
    clearTimeout(timer);
    timer = setTimeout(() => void flush(), 600);
    maximum ??= setTimeout(() => void flush(), 5000);
  }
  async function drain(): Promise<boolean> {
    saving.value = true;
    error.value = "";
    try {
      while (dirty.value) {
        if (paused.value) return false;
        const sent = snapshot();
        const response = await api(`/attempts/${attempt.value._id}`, "PUT", {
          revision: attempt.value.revision,
          ...JSON.parse(sent),
        });
        if (!alive) return true;
        attempt.value.revision = response.revision;
        attempt.value.updated_at = response.updated_at;
        if (snapshot() === sent) {
          answers.value = response.answers;
          // 保存不抢走用户正在编辑的题目；下次恢复使用服务器约束的位置。
          if (!response.path.includes(currentId.value))
            currentId.value = response.current_question_id;
          baseline.value = snapshot();
        } else baseline.value = sent;
      }
      message.value = "已保存到服务器";
      return true;
    } catch (e: any) {
      if (e instanceof ApiError) {
        if (e.status === 401) paused.value = "auth";
        if (e.status === 409) paused.value = "conflict";
      }
      error.value =
        paused.value === "auth"
          ? "登录已过期，当前输入仍保留。请在此重新登录后保存。"
          : e.message;
      message.value = "保存未完成";
      return false;
    } finally {
      saving.value = false;
    }
  }
  async function flush(): Promise<boolean> {
    cancelTimers();
    if (running) return running;
    if (!dirty.value) return true;
    if (!attempt.value || paused.value) return false;
    running = drain();
    try {
      return await running;
    } finally {
      running = null;
    }
  }
  async function reload() {
    if (
      dirty.value &&
      !confirm("重新加载将替换本页未保存的输入，确认使用服务器草稿？")
    )
      return;
    try {
      restore(await api(`/attempts/${attempt.value._id}`));
    } catch (e: any) {
      error.value = e.message;
    }
  }
  async function reauthenticate(username: string, password: string) {
    if (
      username.trim().toLocaleLowerCase() !==
      auth.user?.username.toLocaleLowerCase()
    ) {
      error.value = "请使用当前填写账号重新登录";
      return false;
    }
    try {
      const user = await api("/auth/login", "POST", { username, password });
      if (user.id !== auth.user?.id) {
        error.value = "账号不匹配，未同步当前输入";
        return false;
      }
      auth.user = user;
      paused.value = "";
      return await flush();
    } catch (e: any) {
      error.value = e.message;
      return false;
    }
  }
  onBeforeUnmount(() => {
    alive = false;
    cancelTimers();
  });
  return {
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
  };
}
