import { afterEach, beforeEach, describe, it, expect, vi } from "vitest";
import { mount, flushPromises, type VueWrapper } from "@vue/test-utils";
import { createRouter, createMemoryHistory, RouterView } from "vue-router";
import { defineComponent, h } from "vue";
import { api } from "../../src/api";
import QuestionContentEditor from "../../src/components/QuestionContentEditor.vue";
import QuestionPicker from "../../src/components/QuestionPicker.vue";
import QuestionSharing from "../../src/components/QuestionSharing.vue";
import QuestionEditor from "../../src/views/QuestionEditor.vue";
import QuestionHistory from "../../src/views/QuestionHistory.vue";
import QuestionStatistics from "../../src/views/QuestionStatistics.vue";
import Editor from "../../src/views/Editor.vue";
vi.mock("../../src/api", () => ({
  api: vi.fn(),
  auth: { user: { id: "owner" } },
}));
const request = vi.mocked(api);
const number = {
  type: "number",
  title: "年龄",
  options: [],
  validation: { min: 0, max: 120 },
};
const version = {
  _id: "v1",
  question_id: "bank",
  version: 1,
  content: number,
  parent_version_id: null,
  restored_from_version_id: null,
  created_at: "2026-10-24T00:00:00Z",
};
const question = {
  _id: "bank",
  revision: 2,
  latest_version_id: "v2",
  archived: false,
};
const source = {
  question_id: "bank",
  question_version_id: "v1",
  version: 1,
  survey_id: "survey",
  instance_id: "local",
  imported_by: "owner",
  imported_at: "2026-10-24T00:00:00Z",
  grant_id: null,
};
const survey = {
  _id: "survey",
  revision: 1,
  status: "draft",
  current_version: 0,
  deadline: null,
  share_code: "share",
  draft: {
    title: "调查",
    description: "",
    allow_repeat: true,
    allow_anonymous: true,
    questions: [
      {
        id: "local",
        ...number,
        required: true,
        routing: { rules: [], default_target: null },
        source,
      },
    ],
  },
};
let wrapper: VueWrapper | undefined;
beforeEach(() => {
  request.mockReset();
  vi.spyOn(window, "confirm").mockReturnValue(true);
});
afterEach(() => {
  wrapper?.unmount();
  wrapper = undefined;
  document.body.innerHTML = "";
});
async function routed(component: any, path: string, pattern: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: pattern, component },
      { path: "/:pathMatch(.*)*", component: { template: "<p>其他页面</p>" } },
    ],
  });
  await router.push(path);
  await router.isReady();
  wrapper = mount(
    defineComponent(() => () => h(RouterView)),
    { global: { plugins: [router] }, attachTo: document.body },
  );
  await flushPromises();
  return router;
}
function button(text: string) {
  return wrapper!.findAll("button").find((x) => x.text() === text)!;
}
function pending() {
  let resolve!: (value: any) => void;
  const promise = new Promise<any>((r) => (resolve = r));
  return { promise, resolve };
}

describe("第二阶段题目与权限交互", () => {
  it("题型变化生成独立选项并重置旧校验", async () => {
    const content = structuredClone(number);
    wrapper = mount(QuestionContentEditor, { props: { content } });
    await wrapper.get("select").setValue("multiple_choice");
    expect(content.options).toHaveLength(2);
    expect(content.validation).toEqual({});
    expect((content.options[0] as any).id).not.toBe(
      (content.options[1] as any).id,
    );
  });
  it("选题器只发出用户明确选择的版本ID", async () => {
    request.mockImplementation(async (path) =>
      path === "/libraries"
        ? { items: [] }
        : {
            items: [{ _id: "bank", title: "年龄", versions: [version] }],
            total: 1,
          },
    );
    wrapper = mount(QuestionPicker);
    await flushPromises();
    await button("选择 v1").trigger("click");
    expect(wrapper.emitted("pick")).toEqual([["v1"]]);
  });
  it("归档选项不能被选用", async () => {
    request.mockImplementation(async (path) =>
      path === "/libraries"
        ? { items: [] }
        : {
            items: [
              {
                _id: "bank",
                title: "年龄",
                archived: true,
                versions: [version],
              },
            ],
            total: 1,
          },
    );
    wrapper = mount(QuestionPicker);
    await flushPromises();
    expect(button("选择 v1").attributes("disabled")).toBeDefined();
  });
  it("选题失败给出错误而不伪造空成功", async () => {
    request.mockRejectedValue(new Error("无权访问"));
    wrapper = mount(QuestionPicker);
    await flushPromises();
    expect(wrapper.text()).toContain("无权访问");
    expect(wrapper.emitted("pick")).toBeUndefined();
  });
  it("题目共享只请求指定版本使用权", async () => {
    request.mockResolvedValue({});
    wrapper = mount(QuestionSharing, { props: { versionId: "v1" } });
    await wrapper.get("input").setValue("peer");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(request).toHaveBeenCalledWith("/grants", "POST", {
      kind: "use",
      question_version_id: "v1",
      username: "peer",
    });
  });
  it("汇总授权显式绑定问卷且不请求明细权", async () => {
    request.mockResolvedValue({});
    wrapper = mount(QuestionSharing, {
      props: { versionId: "v1", surveyId: "survey" },
    });
    await wrapper.get("input").setValue("peer");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(request).toHaveBeenCalledWith("/grants", "POST", {
      kind: "aggregate",
      question_version_id: "v1",
      username: "peer",
      survey_id: "survey",
    });
  });
  it("新版本提交携带原父版本与revision", async () => {
    request.mockImplementation(async (path, method) =>
      method === "POST"
        ? { question: { _id: "bank" } }
        : {
            question,
            versions: [version, { ...version, _id: "v2", version: 2 }],
          },
    );
    await routed(
      QuestionEditor,
      "/questions/bank/edit?base=v1",
      "/questions/:id/edit",
    );
    await wrapper!.get('input[maxlength="500"]').setValue("新年龄");
    await wrapper!.get("form").trigger("submit");
    await flushPromises();
    expect(request).toHaveBeenCalledWith(
      "/questions/bank/versions",
      "POST",
      expect.objectContaining({
        revision: 2,
        parent_version_id: "v1",
        content: expect.objectContaining({ title: "新年龄" }),
      }),
    );
  });
  it("版本保存冲突保留用户输入并提示", async () => {
    request.mockImplementation(async (path, method) => {
      if (method === "POST") throw new Error("题目已变化");
      return { question, versions: [version] };
    });
    await routed(
      QuestionEditor,
      "/questions/bank/edit?base=v1",
      "/questions/:id/edit",
    );
    await wrapper!.get('input[maxlength="500"]').setValue("未保存的新内容");
    await wrapper!.get("form").trigger("submit");
    await flushPromises();
    expect(wrapper!.text()).toContain("题目已变化");
    expect(
      (wrapper!.get('input[maxlength="500"]').element as HTMLInputElement)
        .value,
    ).toBe("未保存的新内容");
  });
  it("恢复请求分别记录当前父版本和历史内容来源", async () => {
    request.mockImplementation(async (path, method) =>
      method === "POST"
        ? {}
        : path.includes("/usage")
          ? { scope: "自有", items: [], detail_total: 0 }
          : {
              question,
              versions: [{ ...version, _id: "v2", version: 2 }, version],
            },
    );
    await routed(
      QuestionHistory,
      "/questions/bank/history",
      "/questions/:id/history",
    );
    const buttons = wrapper!
      .findAll("button")
      .filter((b) => b.text() === "恢复此版内容");
    await buttons[1].trigger("click");
    await flushPromises();
    expect(request).toHaveBeenCalledWith("/questions/bank/restore", "POST", {
      revision: 2,
      parent_version_id: "v2",
      restored_from_version_id: "v1",
      change_note: "恢复v1",
    });
  });
  it("来源题内容被锁定而必答可独立编辑", async () => {
    request.mockResolvedValue(structuredClone(survey));
    await routed(Editor, "/surveys/survey/edit", "/surveys/:id/edit");
    expect(
      wrapper!
        .get('input[placeholder="你想了解什么？"]')
        .attributes("disabled"),
    ).toBeDefined();
    expect(
      wrapper!.get(".phase2-content-fieldset").attributes("disabled"),
    ).toBeDefined();
    const required = wrapper!
      .findAll('input[type="checkbox"]')
      .find((i) => (i.element as HTMLInputElement).checked)!;
    expect(required.attributes("disabled")).toBeUndefined();
  });
  it("共享实例不提供解除关联与另存入口", async () => {
    const s = structuredClone(survey);
    s.draft.questions[0].source.grant_id = "grant" as any;
    request.mockResolvedValue(s);
    await routed(Editor, "/surveys/survey/edit", "/surveys/:id/edit");
    expect(wrapper!.text()).not.toContain("解除自有来源");
    expect(wrapper!.text()).not.toContain("保存为常用题（不复制跳转）");
  });
  it("来源操作期间锁定编辑区域并更新服务端来源", async () => {
    const wait = pending();
    request.mockImplementation(async (path, method) =>
      method === "POST" ? wait.promise : structuredClone(survey),
    );
    await routed(Editor, "/surveys/survey/edit", "/surveys/:id/edit");
    await button("保存为常用题（不复制跳转）").trigger("click");
    await flushPromises();
    expect(
      wrapper!.get(".phase2-editor-fieldset").attributes("disabled"),
    ).toBeDefined();
    const updated = structuredClone(survey);
    updated.revision = 2;
    updated.draft.questions[0].source.version = 2;
    wait.resolve({ survey: updated });
    await flushPromises();
    expect(wrapper!.text()).toContain("来源版本 v2");
    expect(
      wrapper!.get(".phase2-editor-fieldset").attributes("disabled"),
    ).toBeUndefined();
  });
  it("统计授权撤销后的失败不会残留旧统计结果", async () => {
    request.mockResolvedValue({
      content: number,
      version: 1,
      coverage_surveys: 1,
      answered_surveys: 1,
      valid_answers: 10,
      valid_responses: 10,
    });
    await routed(
      QuestionStatistics,
      "/question-versions/v1/statistics",
      "/question-versions/:id/statistics",
    );
    expect(wrapper!.text()).toContain("有效答卷");
    request.mockRejectedValue(new Error("无权统计"));
    await wrapper!.get("form").trigger("submit");
    await flushPromises();
    expect(wrapper!.text()).toContain("无权统计");
    expect(wrapper!.text()).not.toContain("有效答卷");
  });
});
