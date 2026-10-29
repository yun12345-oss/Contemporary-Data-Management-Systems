import { afterEach, beforeEach, it, expect, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createRouter, createMemoryHistory, RouterView } from "vue-router";
import { defineComponent, h } from "vue";
import { api } from "../../src/api";
import Editor from "../../src/views/Editor.vue";
import Statistics from "../../src/views/Statistics.vue";
import Libraries from "../../src/views/Libraries.vue";
import QuestionEditor from "../../src/views/QuestionEditor.vue";
import QuestionPicker from "../../src/components/QuestionPicker.vue";
import QuestionHistory from "../../src/views/QuestionHistory.vue";
import { useSurveyEditor } from "../../src/composables/useSurveyEditor";
vi.mock("../../src/api", () => ({
  api: vi.fn(),
  auth: { user: { id: "owner" } },
}));
const request = vi.mocked(api);
let wrapper: any;
beforeEach(() => {
  request.mockReset();
});
afterEach(() => {
  wrapper?.unmount();
  wrapper = undefined;
  document.body.innerHTML = "";
});
async function open(component: any, path: string, pattern: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: pattern, component },
      { path: "/:pathMatch(.*)*", component: { template: "<p>Other</p>" } },
    ],
  });
  await router.push(path);
  await router.isReady();
  wrapper = mount(
    defineComponent(() => () => h(RouterView)),
    { global: { plugins: [router] }, attachTo: document.body },
  );
  await flushPromises();
}
function button(text: string) {
  const b = wrapper.findAll("button").find((x: any) => x.text() === text);
  if (!b) throw Error("Missing button " + text);
  return b;
}
function pending() {
  let resolve!: (value: any) => void;
  const promise = new Promise<any>((r) => (resolve = r));
  return { promise, resolve };
}
const number = {
  type: "number",
  title: "Age",
  options: [],
  validation: { min: 0, max: 120 },
};
function q(id: string) {
  return {
    id,
    ...structuredClone(number),
    required: true,
    routing: { rules: [], default_target: null },
    source: {
      question_id: "bank",
      question_version_id: "v1",
      version: 1,
      survey_id: "survey",
      instance_id: id,
      imported_by: "owner",
      imported_at: "2026-10-25T00:00:00Z",
      grant_id: null,
    },
  };
}
function survey() {
  return {
    _id: "survey",
    revision: 1,
    status: "draft",
    current_version: 0,
    deadline: null,
    share_code: "share",
    created_at: "2026-10-25T00:00:00Z",
    updated_at: "2026-10-25T00:00:00Z",
    draft: {
      title: "Survey",
      description: "",
      allow_repeat: true,
      allow_anonymous: true,
      questions: [q("first"), q("second")],
    },
  };
}

it("upgrade confirmation must apply to the instance shown in its preview", async () => {
  const s = survey();
  request.mockImplementation(async (path, method, body: any) => {
    if (path === "/surveys/survey") return structuredClone(s);
    if (path.startsWith("/questions?"))
      return {
        items: [
          {
            _id: "bank",
            title: "Age",
            versions: [
              {
                _id: "v2",
                version: 2,
                content: { ...number, title: "New age" },
              },
            ],
          },
        ],
        total: 1,
      };
    if (path === "/libraries") return { items: [], total: 0 };
    if (path.endsWith("/upgrade-preview"))
      return {
        diff: [{ field: "title", before: "Age", after: "New age" }],
        issues: [],
        definition: s.draft,
      };
    if (path.endsWith("/upgrade"))
      return { ...structuredClone(s), revision: 2 };
    throw Error("Unexpected " + path);
  });
  await open(Editor, "/surveys/survey/edit", "/surveys/:id/edit");
  await button("选择版本并预览升级").trigger("click");
  await flushPromises();
  await button("选择 v2").trigger("click");
  await flushPromises();
  const previewCall = request.mock.calls.find((c) =>
    c[0].endsWith("/upgrade-preview"),
  )!;
  await wrapper.findAll(".question-nav")[1].trigger("click");
  await flushPromises();
  if (!wrapper.text().includes("确认升级草稿")) return;
  await button("确认升级草稿").trigger("click");
  await flushPromises();
  const applyCall = request.mock.calls.find((c) => c[0].endsWith("/upgrade"))!;
  expect((applyCall[2] as any).instance_id).toBe(
    (previewCall[2] as any).instance_id,
  );
});

it("late old statistics must not overwrite the selected version", async () => {
  const old = pending();
  const stats = (version: number) => ({
    version,
    title: "Survey",
    total: version,
    respondent_count: 1,
    questions: [
      {
        id: "q",
        title: "Age",
        type: "number",
        answered: version,
        respondent_count: 1,
        average: version,
        min: version,
        max: version,
      },
    ],
  });
  request.mockImplementation(async (path) => {
    if (path.endsWith("/versions"))
      return [
        { version: 2, published_at: "2026-10-25T00:00:00Z" },
        { version: 1, published_at: "2026-10-24T00:00:00Z" },
      ];
    if (path.includes("/statistics?version=2")) return old.promise;
    if (path.includes("/statistics?version=1")) return stats(1);
    throw Error("Unexpected " + path);
  });
  await open(
    Statistics,
    "/surveys/survey/statistics",
    "/surveys/:id/statistics",
  );
  await wrapper.get("select").setValue("1");
  await flushPromises();
  expect(wrapper.text()).toContain("v1");
  old.resolve(stats(2));
  await flushPromises();
  expect(wrapper.findAll(".stats-summary strong")[3].text()).toBe("v1");
});

it("a library member with revoked old version must allow choosing an authorized newer version", async () => {
  request.mockImplementation(async (path) => {
    if (path.startsWith("/libraries?"))
      return { items: [{ _id: "library", name: "My Library" }], total: 1 };
    if (path.startsWith("/libraries/library/items"))
      return {
        library: { _id: "library", name: "My Library", revision: 2 },
        items: [
          {
            _id: "member",
            question_id: "bank",
            question_version_id: "v1",
            position: 0,
            available: false,
            version: null,
          },
        ],
        total: 1,
      };
    if (path.startsWith("/questions?"))
      return {
        items: [
          {
            _id: "bank",
            title: "New age",
            versions: [
              {
                _id: "v2",
                version: 2,
                content: { ...number, title: "New age" },
              },
            ],
          },
        ],
        total: 1,
      };
    if (path === "/libraries") return { items: [], total: 0 };
    throw Error("Unexpected " + path);
  });
  await open(Libraries, "/libraries", "/libraries");
  await button("My Library").trigger("click");
  await flushPromises();
  expect(button("更新版本").element.disabled).toBe(false);
});

async function editor(preview?: Promise<any>) {
  const s = survey();
  request.mockImplementation(async (path, method, body: any) => {
    if (path === "/surveys/survey") return structuredClone(s);
    if (path.endsWith("/draft"))
      return { ...structuredClone(s), revision: 2, draft: body.draft };
    if (path.startsWith("/questions?"))
      return {
        items: [
          {
            _id: "bank",
            title: "Age",
            versions: [
              { _id: "v2", version: 2, content: number },
              { _id: "v3", version: 3, content: number },
            ],
          },
        ],
        total: 1,
      };
    if (path === "/libraries") return { items: [], total: 0 };
    if (path.endsWith("/upgrade-preview"))
      return preview ?? { diff: [], issues: [], definition: s.draft };
    if (path.endsWith("/upgrade"))
      return { ...structuredClone(s), revision: 2 };
    throw Error("Unexpected " + path);
  });
  await open(Editor, "/surveys/survey/edit", "/surveys/:id/edit");
  await button("选择版本并预览升级").trigger("click");
  await flushPromises();
  await button("选择 v2").trigger("click");
  await flushPromises();
}
it("normal confirmation sends the exact instance target and preview revision", async () => {
  await editor();
  await button("确认升级草稿").trigger("click");
  await flushPromises();
  expect(
    request.mock.calls.find((c) => c[0].endsWith("/upgrade"))?.[2],
  ).toEqual({ instance_id: "first", question_version_id: "v2", revision: 1 });
});
it("local editing with unchanged server revision invalidates preview", async () => {
  await editor();
  await wrapper.get('input[placeholder="填写问卷标题"]').setValue("Changed");
  await flushPromises();
  expect(wrapper.text()).not.toContain("确认升级草稿");
  expect(request.mock.calls.some((c) => c[0].endsWith("/upgrade"))).toBe(false);
});
it("late preview cannot appear on another instance", async () => {
  const wait = pending();
  await editor(wait.promise);
  await wrapper.findAll(".question-nav")[1].trigger("click");
  wait.resolve({ diff: [], issues: [] });
  await flushPromises();
  expect(wrapper.text()).not.toContain("确认升级草稿");
});
it("closed preview ignores a late response", async () => {
  const wait = pending();
  await editor(wait.promise);
  await button("收起").trigger("click");
  wait.resolve({ diff: [], issues: [] });
  await flushPromises();
  expect(wrapper.text()).not.toContain("确认升级草稿");
});
it("changing target immediately invalidates old confirmation", async () => {
  await editor();
  const wait = pending();
  request.mockImplementation(async (path) =>
    path.endsWith("/upgrade-preview")
      ? wait.promise
      : { ...survey(), revision: 2 },
  );
  await button("选择 v3").trigger("click");
  expect(wrapper.text()).not.toContain("确认升级草稿");
  wait.resolve({ diff: [], issues: [] });
  await flushPromises();
  await button("确认升级草稿").trigger("click");
  expect(
    request.mock.calls.find((c) => c[0].endsWith("/upgrade"))?.[2],
  ).toMatchObject({ question_version_id: "v3", revision: 1 });
});
it("unmounted editor discards late preview", async () => {
  const wait = pending();
  await editor(wait.promise);
  const vm = wrapper;
  vm.unmount();
  wrapper = undefined;
  wait.resolve({ diff: [], issues: [] });
  await flushPromises();
  expect(request.mock.calls.some((c) => c[0].endsWith("/upgrade"))).toBe(false);
});
it("dedicated confirmation refuses dirty draft without auto saving", async () => {
  const state = useSurveyEditor("survey");
  state.survey.value = survey() as any;
  const c = {
    surveyId: "survey",
    instanceId: "first",
    sourceVersionId: "v1",
    targetVersionId: "v2",
    revision: 1,
    draftFingerprint: JSON.stringify(state.survey.value.draft),
    requestId: 1,
  };
  expect(await state.confirmQuestionUpgrade(c)).toBe(false);
  expect(request).not.toHaveBeenCalled();
});
it("dedicated confirmation rejects stale revision and changed source", async () => {
  let state: any;
  request.mockResolvedValue(survey());
  state = useSurveyEditor("survey");
  await state.load();
  request.mockClear();
  const c = {
    surveyId: "survey",
    instanceId: "first",
    sourceVersionId: "wrong",
    targetVersionId: "v2",
    revision: 1,
    draftFingerprint: JSON.stringify(state.survey.value.draft),
    requestId: 1,
  };
  expect(await state.confirmQuestionUpgrade(c)).toBe(false);
  expect(
    await state.confirmQuestionUpgrade({
      ...c,
      sourceVersionId: "v1",
      revision: 0,
    }),
  ).toBe(false);
  expect(request).not.toHaveBeenCalled();
});
const result = (v: number) => ({
  version: v,
  title: "Survey",
  total: 1,
  respondent_count: 1,
  questions: [
    {
      id: "q",
      title: "Text " + v,
      type: "text",
      answered: 1,
      respondent_count: 1,
    },
  ],
});
async function statistics() {
  request.mockImplementation(async (path) => {
    if (path.endsWith("/versions")) return [{ version: 2 }, { version: 1 }];
    if (path.includes("/statistics?"))
      return result(
        Number(new URLSearchParams(path.split("?")[1]).get("version")),
      );
    if (path.includes("/values?"))
      return {
        items: [{ value: "hello", submitted_at: "2026-10-25T00:00:00Z" }],
        total: 1,
      };
    throw Error(path);
  });
  await open(
    Statistics,
    "/surveys/survey/statistics",
    "/surveys/:id/statistics",
  );
}
it("unapplied dates do not change detail query or version label", async () => {
  await statistics();
  await wrapper
    .findAll('input[type="datetime-local"]')[0]
    .setValue("2026-10-01T00:00");
  await button("查看填写内容 ↗").trigger("click");
  await flushPromises();
  expect(
    request.mock.calls.find((c) => c[0].includes("/values?"))?.[0],
  ).toContain("version=2&page=1");
  expect(
    request.mock.calls.find((c) => c[0].includes("/values?"))?.[0],
  ).not.toContain("start=");
  expect(wrapper.text()).toContain("筛选条件尚未应用");
  expect(wrapper.text()).toContain("RESPONSES / v2");
});
it("closing loading details prevents late response reopening", async () => {
  await statistics();
  const wait = pending();
  request.mockImplementation(async () => wait.promise);
  await button("查看填写内容 ↗").trigger("click");
  await wrapper.get('button[aria-label="关闭"]').trigger("click");
  wait.resolve({ items: [{ value: "late" }], total: 1 });
  await flushPromises();
  expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
});
it("switching summary version invalidates old detail response", async () => {
  await statistics();
  const wait = pending();
  request.mockImplementation(async (path) =>
    path.includes("/values?") ? wait.promise : result(1),
  );
  await button("查看填写内容 ↗").trigger("click");
  await wrapper.get("select").setValue("1");
  await flushPromises();
  wait.resolve({ items: [{ value: "late" }], total: 1 });
  await flushPromises();
  expect(wrapper.text()).not.toContain("late");
  expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
});
it("late old error and finally cannot clear latest result or busy state", async () => {
  const old = pending();
  request.mockImplementation(async (path) =>
    path.endsWith("/versions")
      ? [{ version: 2 }, { version: 1 }]
      : path.includes("version=2")
        ? old.promise.then(() => {
            throw Error("old error");
          })
        : result(1),
  );
  await open(
    Statistics,
    "/surveys/survey/statistics",
    "/surveys/:id/statistics",
  );
  await wrapper.get("select").setValue("1");
  await flushPromises();
  old.resolve(null);
  await flushPromises();
  expect(wrapper.text()).not.toContain("old error");
  expect(wrapper.findAll(".stats-summary strong")[3].text()).toBe("v1");
});
it("latest statistics failure clears prior result", async () => {
  await statistics();
  request.mockRejectedValue(new Error("Latest failure"));
  await button("应用筛选").trigger("click");
  await flushPromises();
  expect(wrapper.text()).toContain("Latest failure");
  expect(wrapper.find(".stats-summary").exists()).toBe(false);
});
it("question picker reloads series and ignores late old candidates", async () => {
  const old = pending();
  request.mockImplementation(async (path) =>
    path === "/libraries"
      ? { items: [], total: 0 }
      : path.includes("question_id=A")
        ? old.promise
        : { items: [{ _id: "B", title: "B choice", versions: [] }], total: 1 },
  );
  wrapper = mount(QuestionPicker, { props: { questionId: "A" } });
  await flushPromises();
  await wrapper.setProps({ questionId: "B" });
  await flushPromises();
  old.resolve({
    items: [{ _id: "A", title: "A stale", versions: [] }],
    total: 1,
  });
  await flushPromises();
  expect(wrapper.text()).toContain("B choice");
  expect(wrapper.text()).not.toContain("A stale");
});
async function libraries() {
  request.mockImplementation(async (path, method) => {
    if (path.startsWith("/libraries?"))
      return {
        items: [
          { _id: "L1", name: "Library 1" },
          { _id: "L2", name: "Library 2" },
        ],
        total: 2,
      };
    if (path.includes("/items") && method === "PUT") return {};
    if (path.includes("/items")) {
      const id = path.includes("L1") ? "L1" : "L2";
      return {
        library: { _id: id, name: id, revision: 2 },
        items: [
          {
            _id: "member",
            question_id: "bank",
            position: 0,
            available: false,
            version: null,
          },
        ],
        total: 1,
      };
    }
    if (path.startsWith("/questions?"))
      return {
        items: [
          {
            _id: "bank",
            title: "Age",
            versions: [{ _id: "v2", version: 2, content: number }],
          },
        ],
        total: 1,
      };
    if (path === "/libraries") return { items: [], total: 0 };
    throw Error(path);
  });
  await open(Libraries, "/libraries", "/libraries");
  await button("Library 1").trigger("click");
  await flushPromises();
}
it("switching libraries closes pending update and rejects late candidates", async () => {
  await libraries();
  const wait = pending();
  const impl = request.getMockImplementation()!;
  request.mockImplementation((...args) =>
    args[0].startsWith("/questions?") ? wait.promise : impl(...args),
  );
  await button("更新版本").trigger("click");
  await flushPromises();
  await button("Library 2").trigger("click");
  await flushPromises();
  wait.resolve({
    items: [
      { _id: "bank", title: "stale", versions: [{ _id: "v2", version: 2 }] },
    ],
    total: 1,
  });
  await flushPromises();
  expect(wrapper.text()).not.toContain("选择 v2");
  expect(request.mock.calls.some((c) => c[1] === "PUT")).toBe(false);
});
it("update from unavailable member binds original library member and revision", async () => {
  await libraries();
  await button("更新版本").trigger("click");
  await flushPromises();
  const wait = pending();
  const impl = request.getMockImplementation()!;
  request.mockImplementation((...args) =>
    args[1] === "PUT" ? wait.promise : impl(...args),
  );
  await button("选择 v2").trigger("click");
  expect(button("Library 2").element.disabled).toBe(true);
  expect(request).toHaveBeenCalledWith("/libraries/L1/items/member", "PUT", {
    revision: 2,
    question_version_id: "v2",
    position: 0,
  });
  wait.resolve({});
  await flushPromises();
  expect(wrapper.text()).not.toContain("选择 v2");
});
it("update rejection retains unavailable member and shows error", async () => {
  await libraries();
  await button("更新版本").trigger("click");
  await flushPromises();
  request.mockRejectedValue(new Error("Target revoked"));
  await button("选择 v2").trigger("click");
  await flushPromises();
  expect(wrapper.text()).toContain("Target revoked");
  expect(wrapper.text()).toContain("当前无权读取此版本");
});
it("restore cancel sends no request and confirm sends one request", async () => {
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  request.mockImplementation(async (path, method) =>
    method === "POST"
      ? {}
      : path.includes("/usage")
        ? { items: [], detail_total: 0 }
        : {
            question: { revision: 2, latest_version_id: "v2" },
            versions: [
              { _id: "v2", version: 2, content: number },
              { _id: "v1", version: 1, content: number },
            ],
          },
  );
  await open(
    QuestionHistory,
    "/questions/bank/history",
    "/questions/:id/history",
  );
  const bs = wrapper
    .findAll("button")
    .filter((b: any) => b.text() === "恢复此版内容");
  await bs[1].trigger("click");
  expect(request.mock.calls.some((c) => c[1] === "POST")).toBe(false);
  confirm.mockReturnValue(true);
  await bs[1].trigger("click");
  await bs[1].trigger("click");
  await flushPromises();
  expect(request.mock.calls.filter((c) => c[1] === "POST")).toHaveLength(1);
  expect(request).toHaveBeenCalledWith("/questions/bank/restore", "POST", {
    revision: 2,
    parent_version_id: "v2",
    restored_from_version_id: "v1",
    change_note: "恢复v1",
  });
  confirm.mockRestore();
});

it("selection changed during draft save cancels preview even when switching back", async () => {
  await editor();
  await wrapper.get('input[placeholder="填写问卷标题"]').setValue("Changed");
  const wait = pending();
  const impl = request.getMockImplementation()!;
  request.mockImplementation((...args) =>
    args[0].endsWith("/draft") ? wait.promise : impl(...args),
  );
  const count = request.mock.calls.filter((c) =>
    c[0].endsWith("/upgrade-preview"),
  ).length;
  await button("选择 v2").trigger("click");
  await wrapper.findAll(".question-nav")[1].trigger("click");
  await wrapper.findAll(".question-nav")[0].trigger("click");
  const saved = survey();
  saved.draft.title = "Changed";
  saved.revision = 2;
  wait.resolve(saved);
  await flushPromises();
  expect(
    request.mock.calls.filter((c) => c[0].endsWith("/upgrade-preview")),
  ).toHaveLength(count);
});
it("older detail page cannot overwrite latest page context", async () => {
  await statistics();
  request.mockResolvedValue({ items: [{ value: "page1" }], total: 60 });
  await button("查看填写内容 ↗").trigger("click");
  await flushPromises();
  const old = pending();
  const newer = pending();
  let calls = 0;
  request.mockImplementation(() =>
    ++calls === 1 ? old.promise : newer.promise,
  );
  await button("下一页").trigger("click");
  // Reopen from the still-visible summary to request the first page.
  await button("查看填写内容 ↗").trigger("click");
  newer.resolve({ items: [{ value: "new first page" }], total: 60 });
  await flushPromises();
  old.resolve({ items: [{ value: "stale second page" }], total: 60 });
  await flushPromises();
  expect(wrapper.text()).toContain("new first page");
  expect(wrapper.text()).not.toContain("stale second page");
  expect(wrapper.get(".pagination span").text()).toBe("1 / 3");
});

it("failed upgrade confirmation invalidates preview and requires fresh preview", async () => {
  await editor();
  request.mockRejectedValue(new Error("revision conflict"));
  await button("确认升级草稿").trigger("click");
  await flushPromises();
  expect(wrapper.text()).not.toContain("确认升级草稿");
  expect(wrapper.text()).toContain("请重新加载或保存后重新预览");
  expect(
    request.mock.calls.filter((c) => c[0].endsWith("/upgrade")),
  ).toHaveLength(1);
  expect(request.mock.calls.some((c) => c[0].endsWith("/draft"))).toBe(false);
});
