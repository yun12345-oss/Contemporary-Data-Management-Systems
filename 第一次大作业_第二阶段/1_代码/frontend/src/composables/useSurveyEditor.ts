import { computed, ref, watch } from "vue";
import { api } from "../api";
import type { Definition, Survey } from "../types";

type Metadata = Pick<
  Survey,
  "revision" | "status" | "current_version" | "deadline" | "updated_at"
>;
export type UpgradeContext = {
  surveyId: string;
  instanceId: string;
  sourceVersionId: string;
  targetVersionId: string;
  revision: number;
  draftFingerprint: string;
  requestId: number;
};
export function localDeadline(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}

export function useSurveyEditor(sid: string) {
  const survey = ref<Survey | null>(null),
    deadline = ref(""),
    saved = ref(""),
    publishedDeadline = ref(""),
    error = ref(""),
    message = ref(""),
    operation = ref<"" | "saving" | "publishing" | "closing" | "source">("");
  const dirty = computed(
    () => !!survey.value && JSON.stringify(survey.value.draft) !== saved.value,
  );
  const deadlineDirty = computed(
    () => !!survey.value && deadline.value !== publishedDeadline.value,
  );
  const busy = computed(() => operation.value !== "");
  const pendingChanges = computed(() => dirty.value || deadlineDirty.value);
  const statusText = computed(() =>
    [
      dirty.value ? "有未保存的草稿修改" : "草稿已同步",
      deadlineDirty.value ? "截止时间尚未发布" : "",
    ]
      .filter(Boolean)
      .join(" · "),
  );
  watch(
    [() => (survey.value ? JSON.stringify(survey.value.draft) : ""), deadline],
    () => {
      // 用户继续编辑后，旧的成功提示不应再描述当前尚未保存/发布的状态。
      message.value = "";
    },
    { flush: "sync" },
  );

  async function load() {
    try {
      const incoming = await api<Survey>(`/surveys/${sid}`);
      survey.value = incoming;
      saved.value = JSON.stringify(incoming.draft);
      deadline.value = publishedDeadline.value = localDeadline(
        incoming.deadline,
      );
    } catch (e: any) {
      error.value = e.message;
    }
  }
  function metadata(incoming: Metadata) {
    if (!survey.value) return;
    // 只合并服务器元数据，绝不以响应中的 draft 覆盖当前输入。
    survey.value.revision = incoming.revision;
    survey.value.status = incoming.status;
    survey.value.current_version = incoming.current_version;
    survey.value.deadline = incoming.deadline;
    survey.value.updated_at = incoming.updated_at;
  }
  function snapshot(): Definition {
    return JSON.parse(JSON.stringify(survey.value!.draft));
  }
  async function persist(draft: Definition) {
    const response = await api<Survey>(`/surveys/${sid}/draft`, "PUT", {
      revision: survey.value!.revision,
      draft,
    });
    metadata(response);
    survey.value!.draft_issues = response.draft_issues;
    saved.value = JSON.stringify(response.draft);
  }
  function saveFeedback() {
    return [
      dirty.value ? "本次草稿已保存；等待期间的新修改仍未保存" : "草稿已保存",
      deadlineDirty.value ? "截止时间尚未发布，发布新版本后生效" : "",
    ]
      .filter(Boolean)
      .join("；");
  }
  async function save() {
    if (busy.value || !survey.value) return false;
    operation.value = "saving";
    error.value = "";
    message.value = "";
    try {
      await persist(snapshot());
      message.value = saveFeedback();
      return true;
    } catch (e: any) {
      error.value = e.message;
      return false;
    } finally {
      operation.value = "";
    }
  }
  async function publish() {
    if (busy.value || !survey.value) return false;
    if (
      !window.confirm(
        "发布本次确认的内容与截止时间为新版本？历史版本和答案会保留。",
      )
    )
      return false;
    const draft = snapshot(),
      deadlineSnapshot = deadline.value;
    operation.value = "publishing";
    error.value = "";
    message.value = "";
    try {
      const deadlineToPublish =
        deadlineSnapshot === publishedDeadline.value
          ? survey.value.deadline
          : deadlineSnapshot
            ? new Date(deadlineSnapshot).toISOString()
            : null;
      if (dirty.value) await persist(draft);
      if (dirty.value || deadline.value !== deadlineSnapshot) {
        message.value =
          "保存期间有新的修改，本次未发布。修改已保留，请检查后再次发布。";
        return false;
      }
      const response = await api<{ version: number; survey: Metadata }>(
        `/surveys/${sid}/publish`,
        "POST",
        { revision: survey.value.revision, deadline: deadlineToPublish },
      );
      metadata(response.survey);
      publishedDeadline.value = localDeadline(response.survey.deadline);
      message.value =
        `已发布 v${response.version}` +
        (pendingChanges.value
          ? "；等待期间的新修改已保留，尚未保存或发布"
          : "，可以分享填写链接");
      return true;
    } catch (e: any) {
      error.value = e.message;
      return false;
    } finally {
      operation.value = "";
    }
  }
  async function close() {
    if (busy.value || !survey.value) return false;
    operation.value = "closing";
    error.value = "";
    message.value = "";
    let savedDuringClose = false;
    try {
      if (dirty.value) {
        await persist(snapshot());
        savedDuringClose = true;
      }
      if (dirty.value) {
        message.value =
          "保存期间有新的草稿修改，本次未关闭。请检查后再次确认。";
        return false;
      }
      const response = await api<{ ok: boolean; survey: Metadata }>(
        `/surveys/${sid}/status`,
        "PATCH",
        { status: "closed", revision: survey.value.revision },
      );
      metadata(response.survey);
      message.value =
        "问卷已关闭" +
        (dirty.value ? "；等待期间的新草稿修改仍未保存" : "") +
        (deadlineDirty.value
          ? "；截止时间尚未发布，仍保留在本页，关闭不会使其生效"
          : "");
      return true;
    } catch (e: any) {
      error.value =
        (savedDuringClose ? "草稿已保存，但关闭失败：" : "") + e.message;
      return false;
    } finally {
      operation.value = "";
    }
  }
  function canLeave() {
    if (busy.value) {
      error.value = "操作进行中，请等待完成后再离开";
      return false;
    }
    return (
      !pendingChanges.value ||
      window.confirm(
        "有未保存的草稿或尚未发布的截止时间，确认离开并放弃这些本地修改？",
      )
    );
  }
  async function sourceOperation(
    path: string,
    body: Record<string, any>,
    preview?: UpgradeContext,
  ) {
    if (busy.value || !survey.value) return false;
    operation.value = "source";
    error.value = "";
    message.value = "";
    try {
      if (path === "upgrade") {
        const instance = survey.value.draft.questions.find(
          (q) => q.id === preview?.instanceId,
        );
        if (
          !preview ||
          preview.surveyId !== sid ||
          dirty.value ||
          survey.value.revision !== preview.revision ||
          JSON.stringify(survey.value.draft) !== preview.draftFingerprint ||
          instance?.source?.question_version_id !== preview.sourceVersionId ||
          body.instance_id !== preview.instanceId ||
          body.question_version_id !== preview.targetVersionId
        ) {
          throw new Error("升级预览已失效，请保存后重新预览");
        }
      } else if (dirty.value) await persist(snapshot());
      if (dirty.value) throw new Error("仍有新的本地修改，请先保存后重试");
      const result = await api<any>(
        `/surveys/${sid}/questions/${path}`,
        "POST",
        { ...body, revision: preview?.revision ?? survey.value.revision },
      );
      const incoming: Survey = result.survey || result;
      metadata(incoming);
      survey.value.draft = incoming.draft;
      survey.value.draft_issues = incoming.draft_issues;
      saved.value = JSON.stringify(incoming.draft);
      message.value = incoming.draft_issues?.length
        ? "草稿已更新，存在待修复问题；修复后才可发布"
        : "草稿已更新，已发布版本保持不变";
      return true;
    } catch (e: any) {
      error.value = e.message;
      return false;
    } finally {
      operation.value = "";
    }
  }
  function confirmQuestionUpgrade(context: UpgradeContext) {
    return sourceOperation(
      "upgrade",
      {
        instance_id: context.instanceId,
        question_version_id: context.targetVersionId,
      },
      context,
    );
  }
  function unload(e: BeforeUnloadEvent) {
    if (pendingChanges.value || busy.value) {
      e.preventDefault();
      e.returnValue = "";
    }
  }
  return {
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
    sourceOperation,
    confirmQuestionUpgrade,
  };
}
