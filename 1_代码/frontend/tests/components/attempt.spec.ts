import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount, flushPromises, type VueWrapper } from "@vue/test-utils";
import { defineComponent, h } from "vue";
import { createRouter, createMemoryHistory, RouterView } from "vue-router";
import { api, ApiError, auth } from "../../src/api";
import { useAttempt } from "../../src/composables/useAttempt";
import { draftPath, pruneSkipped } from "../../src/attempt-progress";
import Fill from "../../src/views/Fill.vue";
import NumberInput from "../../src/question-types/NumberInput.vue";
import { pendingWork } from "../../src/pending-work";
vi.mock("../../src/api", async (original) => ({
  ...(await original<any>()),
  api: vi.fn(),
}));
const request = vi.mocked(api);
const text = (id: string, required = true) => ({
  id,
  type: "text",
  title: id,
  required,
  options: [],
  validation: {},
  routing: { rules: [], default_target: null },
});
const doc = () => ({
  _id: "attempt",
  revision: 1,
  status: "in_progress",
  anonymous: true,
  updated_at: "2026-10-20T00:00:00Z",
  read_only: false,
  answers: {},
  current_question_id: "q1",
  path: ["q1"],
  definition: {
    title: "续填测试",
    description: "",
    allow_repeat: true,
    allow_anonymous: true,
    questions: [text("q1"), text("q2")],
  },
  version: 1,
});
function deferred() {
  let resolve!: (v: any) => void;
  const promise = new Promise<any>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}
const saved = (answers: any, revision = 2, current = "q1") => ({
  ...doc(),
  answers,
  revision,
  current_question_id: current,
  path: ["q1", "q2"],
});
let wrapper: VueWrapper | undefined;
let state: ReturnType<typeof useAttempt>;
function harness() {
  wrapper = mount(
    defineComponent({
      setup() {
        state = useAttempt();
        return () => h("div");
      },
    }),
  );
  state.restore(doc());
}
beforeEach(() => {
  vi.useFakeTimers();
  request.mockReset();
  auth.user = { id: "user", username: "demo" };
});
afterEach(() => {
  wrapper?.unmount();
  wrapper = undefined;
  vi.useRealTimers();
});

describe("填写自动保存状态", () => {
  it("暂停输入后保存原始内容", async () => {
    harness();
    request.mockResolvedValue(saved({ q1: "半份答案" }));
    state.answers.value.q1 = "半份答案";
    state.changed();
    await vi.advanceTimersByTimeAsync(600);
    expect(request).toHaveBeenCalledWith("/attempts/attempt", "PUT", {
      revision: 1,
      answers: { q1: "半份答案" },
      current_question_id: "q1",
    });
    expect(state.dirty.value).toBe(false);
  });
  it("持续输入也在最长等待时间同步", async () => {
    harness();
    request.mockImplementation(async (_p, _m, b: any) => saved(b.answers));
    for (let i = 0; i < 12; i++) {
      state.answers.value.q1 = String(i);
      state.changed();
      await vi.advanceTimersByTimeAsync(450);
    }
    expect(request).toHaveBeenCalled();
  });
  it("旧响应不把新输入标记为已保存，并串行补存", async () => {
    harness();
    const first = deferred(),
      second = deferred();
    request
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    state.answers.value.q1 = "旧";
    const saving = state.flush();
    state.answers.value.q1 = "新";
    state.changed();
    first.resolve(saved({ q1: "旧" }));
    await flushPromises();
    expect(state.answers.value.q1).toBe("新");
    expect(state.dirty.value).toBe(true);
    expect(state.saving.value).toBe(true);
    expect(request.mock.calls[1][2]).toMatchObject({
      revision: 2,
      answers: { q1: "新" },
    });
    second.resolve(saved({ q1: "新" }, 3));
    expect(await saving).toBe(true);
    expect(state.dirty.value).toBe(false);
  });
  it("重复触发保存复用正在执行的请求", async () => {
    harness();
    const pending = deferred();
    request.mockReturnValue(pending.promise);
    state.answers.value.q1 = "内容";
    const a = state.flush(),
      b = state.flush();
    expect(request).toHaveBeenCalledTimes(1);
    pending.resolve(saved({ q1: "内容" }));
    expect(await a).toBe(true);
    expect(await b).toBe(true);
  });
  it("保存失败保留输入，重试后才清除未保存标记", async () => {
    harness();
    state.answers.value.q1 = "不要丢失";
    request.mockRejectedValueOnce(new Error("网络不可用"));
    expect(await state.flush()).toBe(false);
    expect(state.dirty.value).toBe(true);
    expect(state.answers.value.q1).toBe("不要丢失");
    request.mockResolvedValue(saved({ q1: "不要丢失" }));
    expect(await state.flush()).toBe(true);
  });
  it("冲突暂停自动保存且取消重新加载不丢输入", async () => {
    harness();
    state.answers.value.q1 = "本页修改";
    request.mockRejectedValue(new ApiError("冲突", 409, null));
    expect(await state.flush()).toBe(false);
    expect(state.paused.value).toBe("conflict");
    state.changed();
    await vi.advanceTimersByTimeAsync(6000);
    expect(request).toHaveBeenCalledTimes(1);
    vi.spyOn(window, "confirm").mockReturnValue(false);
    await state.reload();
    expect(state.answers.value.q1).toBe("本页修改");
  });
  it("登录过期后原页同账号登录，再保存未同步输入", async () => {
    harness();
    state.answers.value.q1 = "登录过期仍保留";
    request.mockRejectedValueOnce(new ApiError("请登录", 401, null));
    expect(await state.flush()).toBe(false);
    expect(state.paused.value).toBe("auth");
    expect(await state.reauthenticate("other", "pw")).toBe(false);
    expect(request).toHaveBeenCalledTimes(1);
    request
      .mockResolvedValueOnce({ id: "user", username: "demo" })
      .mockResolvedValueOnce(saved({ q1: "登录过期仍保留" }));
    expect(await state.reauthenticate("demo", "password")).toBe(true);
    expect(state.answers.value.q1).toBe("登录过期仍保留");
    expect(state.dirty.value).toBe(false);
  });
  it("保存响应不抢走用户返回的前题位置", async () => {
    harness();
    state.answers.value.q1 = "完成";
    request.mockResolvedValue(saved({ q1: "完成" }, 2, "q2"));
    await state.flush();
    expect(state.currentId.value).toBe("q1");
  });
  it("只读恢复不触发保存", async () => {
    harness();
    state.restore({
      ...saved({ q1: "已保存" }),
      read_only: true,
      read_only_reason: "已截止",
    });
    state.changed();
    await vi.advanceTimersByTimeAsync(6000);
    expect(request).not.toHaveBeenCalled();
    expect(state.message.value).toBe("已截止");
    expect(state.answers.value.q1).toBe("已保存");
  });
});

async function openFill(resume: any = doc()) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/survey/:share", component: Fill },
      { path: "/", component: { template: "<div>home</div>" } },
    ],
  });
  await router.push("/survey/share");
  await router.isReady();
  request.mockResolvedValueOnce(resume);
  wrapper = mount(defineComponent({ render: () => h(RouterView) }), {
    global: { plugins: [router] },
  });
  await flushPromises();
  return router;
}
describe("恢复页面与输入", () => {
  it("先选择继续，再恢复答案及固定匿名设置", async () => {
    await openFill(saved({ q1: "之前的输入" }));
    expect(wrapper!.text()).toContain("找到一份未完成填写");
    await wrapper!.get("button.primary").trigger("click");
    expect(wrapper!.get("textarea").element.value).toBe("之前的输入");
    expect(wrapper!.text()).toContain("匿名填写");
    expect(wrapper!.find('input[type="checkbox"]').exists()).toBe(false);
  });
  it("数字中间状态原样发送，恢复后仍可编辑", async () => {
    wrapper = mount(NumberInput, {
      props: { question: { ...text("q1"), type: "number" }, modelValue: "-" },
    });
    expect(wrapper.get("input").element.value).toBe("-");
    await wrapper.get("input").setValue("1.");
    expect(wrapper.emitted("update:modelValue")!.at(-1)).toEqual(["1."]);
  });
  it("提交前等待最新保存完成，提交只携带revision", async () => {
    const d = doc();
    d.definition.questions = [text("q1")];
    d.answers = { q1: "旧输入" } as any;
    await openFill(d);
    await wrapper!.get("button.primary").trigger("click");
    const pending = deferred();
    request.mockReturnValueOnce(pending.promise).mockResolvedValueOnce({
      id: "receipt",
      version: 1,
      submitted_at: "2026-10-20T00:00:00Z",
    });
    await wrapper!.get("textarea").setValue("最新输入");
    await wrapper!.get(".fill-navigation button.primary").trigger("click");
    expect(
      request.mock.calls.filter((c) => c[0].endsWith("/submit")),
    ).toHaveLength(0);
    expect(wrapper!.get("fieldset").attributes("disabled")).toBeDefined();
    pending.resolve(saved({ q1: "最新输入" }, 2));
    await flushPromises();
    expect(request).toHaveBeenLastCalledWith(
      "/attempts/attempt/submit",
      "POST",
      { revision: 2 },
    );
    expect(wrapper!.text()).toContain("感谢你的认真回答");
    request.mockResolvedValueOnce(null).mockResolvedValueOnce({
      title: "续填测试",
      allow_repeat: true,
      allow_anonymous: true,
      version: 1,
      question_count: 1,
    });
    await wrapper!.get("button.primary").trigger("click");
    await flushPromises();
    expect(wrapper!.text()).toContain("开始填写");
    expect(wrapper!.get('input[type="checkbox"]').exists()).toBe(true);
  });
  it("主动退出前保存失败必须确认，取消则保留输入", async () => {
    await openFill();
    await wrapper!.get("button.primary").trigger("click");
    await wrapper!.get("textarea").setValue("未同步内容");
    request.mockRejectedValue(new Error("网络失败"));
    vi.spyOn(window, "confirm").mockReturnValue(false);
    expect(await pendingWork.beforeLogout!()).toBe(false);
    expect(wrapper!.get("textarea").element.value).toBe("未同步内容");
  });
  it("截止后的草稿仍可进入只读页面查看全部已保存内容", async () => {
    await openFill({
      ...saved({ q1: "前题", q2: "后题" }),
      read_only: true,
      read_only_reason: "问卷已关闭",
    });
    await wrapper!.get("button.primary").trigger("click");
    expect(wrapper!.text()).toContain("问卷已关闭");
    expect(wrapper!.get("fieldset").attributes("disabled")).toBeDefined();
    expect(wrapper!.get("details").text()).toContain("后题");
    expect(request).toHaveBeenCalledTimes(1);
  });
  it("路由离开先保存，失败且取消时仍停留原页面", async () => {
    const router = await openFill();
    await wrapper!.get("button.primary").trigger("click");
    await wrapper!.get("textarea").setValue("还没有保存");
    request.mockRejectedValue(new Error("网络失败"));
    vi.spyOn(window, "confirm").mockReturnValue(false);
    await router.push("/");
    expect(router.currentRoute.value.path).toBe("/survey/share");
    expect(wrapper!.get("textarea").element.value).toBe("还没有保存");
    request.mockResolvedValue(saved({ q1: "还没有保存" }));
    await router.push("/");
    expect(router.currentRoute.value.path).toBe("/");
  });
  it("未完成前题不使用无效数值跳转，也不误删后续暂存内容", () => {
    const d: any = doc().definition;
    d.questions = [
      {
        ...text("q1"),
        type: "number",
        validation: { min: 0 },
        routing: {
          rules: [
            {
              condition: { question_id: "q1", operator: "gt", value: 2 },
              target: "q3",
            },
          ],
          default_target: null,
        },
      },
      text("q2"),
      text("q3"),
    ];
    const raw: any = { q1: "-", q2: "第二题", q3: "第三题" };
    expect(draftPath(d, raw).map((q) => q.id)).toEqual(["q1"]);
    pruneSkipped(d, raw);
    expect(raw.q3).toBe("第三题");
    raw.q1 = "3";
    pruneSkipped(d, raw);
    expect(raw.q2).toBeUndefined();
    expect(draftPath(d, raw).map((q) => q.id)).toEqual(["q1", "q3"]);
  });
});
