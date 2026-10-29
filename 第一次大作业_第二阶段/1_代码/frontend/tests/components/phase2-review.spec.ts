import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount, flushPromises, type VueWrapper } from "@vue/test-utils";
import { createRouter, createMemoryHistory, RouterView } from "vue-router";
import { defineComponent, h } from "vue";
import { api } from "../../src/api";
import Sharing from "../../src/views/Sharing.vue";
import Questions from "../../src/views/Questions.vue";
import QuestionUsagePage from "../../src/views/QuestionUsage.vue";
import QuestionUsage from "../../src/components/QuestionUsage.vue";
import QuestionPicker from "../../src/components/QuestionPicker.vue";
import QuestionStatistics from "../../src/views/QuestionStatistics.vue";
vi.mock("../../src/api", () => ({
  api: vi.fn(),
  auth: { user: { id: "recipient" } },
}));
const request = vi.mocked(api);
let wrapper: VueWrapper | undefined;
beforeEach(() => {
  request.mockReset();
});
afterEach(() => {
  wrapper?.unmount();
  wrapper = undefined;
  document.body.innerHTML = "";
});
async function open(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/sharing", component: Sharing },
      { path: "/questions", component: Questions },
      { path: "/questions/:id/usage", component: QuestionUsagePage },
      {
        path: "/question-versions/:id/statistics",
        component: QuestionStatistics,
      },
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
const summary = {
  content: { title: "年龄", type: "number" },
  version: 1,
  coverage_surveys: 1,
  answered_surveys: 1,
  valid_responses: 1,
  valid_answers: 1,
};
function button(text: string) {
  const b = wrapper!.findAll("button").find((b) => b.text() === text);
  if (!b) throw Error("Missing " + text);
  return b;
}
function pending() {
  let resolve!: (x: any) => void;
  const promise = new Promise<any>((r) => (resolve = r));
  return { promise, resolve };
}
const libs = Array.from({ length: 20 }, (_, i) => ({
  _id: "lib" + i,
  name: "题库" + i,
}));

describe("第二阶段五项审阅修复", () => {
  it("仅统计授权从共享页直接打开指定问卷统计", async () => {
    request.mockImplementation(async (path) =>
      path.startsWith("/grants")
        ? {
            items: [
              {
                _id: "grant",
                active: true,
                kind: "aggregate",
                question_version_id: "v1",
                survey_id: "survey1",
                grantee_id: "recipient",
                grantor_id: "owner",
              },
            ],
            total: 1,
          }
        : summary,
    );
    const router = await open("/sharing");
    const link = wrapper!.get("a.button.primary");
    expect(link.text()).toBe("查看授权统计");
    await link.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.path).toBe(
      "/question-versions/v1/statistics",
    );
    expect(request).toHaveBeenCalledWith(
      expect.stringContaining("survey_id=survey1"),
    );
    expect(request.mock.calls.some(([path]) => path === "/questions")).toBe(
      false,
    );
  });
  it("撤销记录、使用授权和非接收者不提供统计直达入口", async () => {
    request.mockResolvedValue({
      items: [
        { _id: "a", active: false, kind: "aggregate", grantee_id: "recipient" },
        { _id: "b", active: true, kind: "use", grantee_id: "recipient" },
        {
          _id: "c",
          active: true,
          kind: "aggregate",
          grantee_id: "someone",
          grantor_id: "recipient",
        },
      ],
      total: 3,
    });
    await open("/sharing");
    expect(
      wrapper!.findAll("a").filter((a) => a.text() === "查看授权统计"),
    ).toHaveLength(0);
  });
  it("共享接收者从列表进入独立使用页而不调用所有者历史", async () => {
    request.mockImplementation(async (path) =>
      path.startsWith("/questions?")
        ? {
            items: [
              { _id: "bank", owned: false, title: "共享年龄", versions: [] },
            ],
            total: 1,
          }
        : path.startsWith("/questions/bank/usage")
          ? {
              scope: "仅自有问卷",
              used_surveys: 1,
              draft_surveys: 1,
              current_published_surveys: 0,
              historical_published_surveys: 0,
              items: [
                {
                  survey_id: "mine",
                  title: "我的问卷",
                  published_versions: [],
                },
              ],
              detail_total: 1,
            }
          : Promise.reject(new Error("不应调用所有者接口")),
    );
    await open("/questions");
    expect(wrapper!.text()).not.toContain("历史与使用");
    await wrapper!
      .findAll("a")
      .find((a) => a.text() === "使用情况")!
      .trigger("click");
    await flushPromises();
    expect(wrapper!.text()).toContain("仅自有问卷");
    expect(wrapper!.text()).toContain("我的问卷");
    expect(
      request.mock.calls.some(([path]) => path === "/questions/bank"),
    ).toBe(false);
  });
  it("使用追踪后续请求失败时清除旧详情", async () => {
    request.mockResolvedValue({
      scope: "仅自有问卷",
      used_surveys: 30,
      items: [{ survey_id: "mine", title: "旧详情", published_versions: [] }],
      detail_total: 30,
    });
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/:pathMatch(.*)*", component: { template: "<p/>" } }],
    });
    await router.push("/");
    wrapper = mount(QuestionUsage, {
      props: { questionId: "bank" },
      global: { plugins: [router] },
    });
    await flushPromises();
    expect(wrapper.text()).toContain("旧详情");
    request.mockRejectedValue(new Error("无权访问"));
    await button("下一页").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("无权访问");
    expect(wrapper.text()).not.toContain("旧详情");
  });
  it("加载第二页题库后可以选择第21个并查询其成员", async () => {
    request.mockImplementation(async (path) =>
      path === "/libraries"
        ? { items: libs, total: 21 }
        : path === "/libraries?page=2"
          ? { items: [{ _id: "last", name: "第21个题库" }], total: 21 }
          : { items: [], total: 0 },
    );
    wrapper = mount(QuestionPicker);
    await flushPromises();
    expect(wrapper.findAll("option")).toHaveLength(21);
    await button("加载更多题库").trigger("click");
    await flushPromises();
    expect(wrapper.findAll("option")).toHaveLength(22);
    await wrapper.get("select").setValue("last");
    await flushPromises();
    expect(request).toHaveBeenCalledWith(
      "/libraries/last/items?page=1&search=",
    );
    expect(wrapper.text()).not.toContain("加载更多题库");
  });
  it("题库第二页失败可重试，保留已加载列表且不跳页", async () => {
    let fail = true;
    request.mockImplementation(async (path) => {
      if (path === "/libraries") return { items: libs, total: 21 };
      if (path === "/libraries?page=2") {
        if (fail) throw new Error("暂时失败");
        return { items: [{ _id: "last", name: "最后题库" }], total: 21 };
      }
      return { items: [], total: 0 };
    });
    wrapper = mount(QuestionPicker);
    await flushPromises();
    await button("加载更多题库").trigger("click");
    await flushPromises();
    expect(wrapper.findAll("option")).toHaveLength(21);
    expect(wrapper.text()).toContain("题库列表加载失败");
    fail = false;
    await button("重试题库列表").trigger("click");
    await flushPromises();
    expect(wrapper.findAll("option")).toHaveLength(22);
    expect(wrapper.text()).not.toContain("暂时失败");
    expect(
      request.mock.calls.filter(([p]) => p === "/libraries?page=2"),
    ).toHaveLength(2);
  });
  it("题库内查询携带关键词并显示服务端筛选后的总页数", async () => {
    request.mockImplementation(async (path) =>
      path === "/libraries"
        ? { items: [{ _id: "lib", name: "题库" }], total: 1 }
        : path.includes("/items")
          ? {
              items: [
                {
                  question_id: "q",
                  version: { _id: "v", version: 1, content: { title: "目标" } },
                  available: true,
                },
              ],
              total: 1,
            }
          : { items: [], total: 0 },
    );
    wrapper = mount(QuestionPicker);
    await flushPromises();
    await wrapper.get("input").setValue("目标 [x]");
    await wrapper.get("select").setValue("lib");
    await flushPromises();
    expect(request).toHaveBeenCalledWith(
      "/libraries/lib/items?page=1&search=" + encodeURIComponent("目标 [x]"),
    );
    expect(wrapper.text()).toContain("目标");
    expect(button("下一页").attributes("disabled")).toBeDefined();
  });
  it("题库升级选择器将系列过滤传给后端", async () => {
    request.mockImplementation(async (path) =>
      path === "/libraries"
        ? { items: [{ _id: "lib", name: "题库" }], total: 1 }
        : { items: [], total: 0 },
    );
    wrapper = mount(QuestionPicker, { props: { questionId: "bank" } });
    await flushPromises();
    await wrapper.get("select").setValue("lib");
    await flushPromises();
    expect(request).toHaveBeenCalledWith(
      "/libraries/lib/items?page=1&search=&question_id=bank",
    );
  });
  it("搜索失败清除旧可选项，避免误选上一份结果", async () => {
    request.mockImplementation(async (path) =>
      path === "/libraries"
        ? { items: [], total: 0 }
        : {
            items: [
              {
                _id: "q",
                title: "旧结果",
                versions: [{ _id: "v", version: 1 }],
              },
            ],
            total: 1,
          },
    );
    wrapper = mount(QuestionPicker);
    await flushPromises();
    expect(wrapper.text()).toContain("旧结果");
    request.mockRejectedValue(new Error("检索失败"));
    await button("查询").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("检索失败");
    expect(wrapper.text()).not.toContain("旧结果");
  });
  it("迟到的旧搜索结果不能覆盖新关键词的结果", async () => {
    const wait = pending();
    request.mockImplementation(async (path) =>
      path === "/libraries"
        ? { items: [], total: 0 }
        : path.includes("search=old")
          ? wait.promise
          : path.includes("search=new")
            ? {
                items: [{ _id: "new", title: "新结果", versions: [] }],
                total: 1,
              }
            : { items: [], total: 0 },
    );
    wrapper = mount(QuestionPicker);
    await flushPromises();
    await wrapper.get("input").setValue("old");
    await wrapper.get("input").trigger("keyup.enter");
    await wrapper.get("input").setValue("new");
    await wrapper.get("input").trigger("keyup.enter");
    await flushPromises();
    expect(wrapper.text()).toContain("新结果");
    wait.resolve({
      items: [{ _id: "old", title: "迟到旧结果", versions: [] }],
      total: 1,
    });
    await flushPromises();
    expect(wrapper.text()).toContain("新结果");
    expect(wrapper.text()).not.toContain("迟到旧结果");
  });
});
