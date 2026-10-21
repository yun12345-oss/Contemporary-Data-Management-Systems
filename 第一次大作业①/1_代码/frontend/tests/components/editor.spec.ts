import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount, flushPromises, type VueWrapper } from "@vue/test-utils";
import { createRouter, createMemoryHistory, RouterView } from "vue-router";
import { defineComponent, h } from "vue";
import Editor from "../../src/views/Editor.vue";
import { api } from "../../src/api";
vi.mock("../../src/api", () => ({ api: vi.fn() }));
const request = vi.mocked(api);
const initial = {
  _id: "survey",
  share_code: "share",
  status: "published",
  revision: 1,
  current_version: 1,
  deadline: null,
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
  draft: {
    title: "原始问卷",
    description: "说明",
    allow_anonymous: true,
    allow_repeat: true,
    questions: [
      {
        id: "q1",
        type: "text",
        title: "建议",
        required: false,
        options: [],
        validation: {},
        routing: { rules: [], default_target: null },
      },
    ],
  },
};
const meta = (
  revision = 2,
  status = "published",
  deadline: string | null = null,
) => ({
  revision,
  status,
  current_version: status === "published" ? 2 : 1,
  deadline,
  updated_at: "2026-10-19T00:00:00Z",
});
function deferred<T = any>() {
  let resolve!: (v: T) => void, reject!: (e: Error) => void;
  const promise = new Promise<T>((a, b) => {
    resolve = a;
    reject = b;
  });
  return { promise, resolve, reject };
}
let wrapper: VueWrapper, router: ReturnType<typeof createRouter>;
async function open() {
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/surveys/:id/edit", component: Editor },
      { path: "/outside", component: { template: "<p>外部页面</p>" } },
      { path: "/:pathMatch(.*)*", component: { template: "<p>其他页面</p>" } },
    ],
  });
  await router.push("/surveys/survey/edit");
  await router.isReady();
  wrapper = mount(
    defineComponent(() => () => h(RouterView)),
    { global: { plugins: [router] }, attachTo: document.body },
  );
  await flushPromises();
  return wrapper;
}
function button(text: string) {
  const b = wrapper.findAll("button").find((b) => b.text() === text);
  if (!b) throw Error("button missing: " + text);
  return b;
}
const title = () => wrapper.get('input[aria-label="问卷标题"]');
const deadline = () => wrapper.get('input[type="datetime-local"]');
beforeEach(() => {
  request.mockReset();
  request.mockImplementation(async () => structuredClone(initial));
  vi.spyOn(window, "confirm").mockReturnValue(true);
});
afterEach(() => {
  wrapper?.unmount();
  document.body.innerHTML = "";
});

describe("编辑器保存、关闭、发布和离开", () => {
  it("继续编辑后清除过期的保存反馈，修改状态仍正确", async () => {
    request.mockImplementation(async (_p, m, b: any) =>
      m === "PUT"
        ? { ...structuredClone(initial), revision: 2, draft: b.draft }
        : structuredClone(initial),
    );
    await open();
    await deadline().setValue("2030-01-01T12:30");
    await button("保存草稿").trigger("click");
    await flushPromises();
    expect(wrapper.find('[role="status"].success').text()).toContain(
      "草稿已保存",
    );
    await deadline().setValue("");
    await title().setValue("新的编辑");
    expect(wrapper.find('[role="status"].success').exists()).toBe(false);
    expect(wrapper.text()).toContain("有未保存的草稿修改");
  });
  it("保存响应不覆盖等待期间的新输入，下一次保存使用新revision", async () => {
    const save = deferred();
    request.mockImplementation(async (_p, m) =>
      m === "PUT" ? save.promise : structuredClone(initial),
    );
    await open();
    await title().setValue("请求时的标题");
    await button("保存草稿").trigger("click");
    expect(request.mock.calls.find((c) => c[1] === "PUT")?.[2]).toMatchObject({
      revision: 1,
      draft: { title: "请求时的标题" },
    });
    await title().setValue("等待期间的新标题");
    save.resolve({
      ...structuredClone(initial),
      revision: 2,
      draft: { ...structuredClone(initial.draft), title: "请求时的标题" },
    });
    await flushPromises();
    expect((title().element as HTMLInputElement).value).toBe(
      "等待期间的新标题",
    );
    expect(wrapper.text()).toContain("有未保存的草稿修改");
    await button("保存草稿").trigger("click");
    expect(
      request.mock.calls.filter((c) => c[1] === "PUT").at(-1)?.[2],
    ).toMatchObject({ revision: 2, draft: { title: "等待期间的新标题" } });
  });
  it("保存失败保留草稿并恢复操作按钮", async () => {
    request.mockImplementation(async (_p, m) => {
      if (m === "PUT") throw Error("网络错误");
      return structuredClone(initial);
    });
    await open();
    await title().setValue("不能丢失");
    await button("保存草稿").trigger("click");
    await flushPromises();
    expect((title().element as HTMLInputElement).value).toBe("不能丢失");
    expect(wrapper.text()).toContain("网络错误");
    expect(wrapper.text()).toContain("有未保存的草稿修改");
    expect(button("保存草稿").attributes("disabled")).toBeUndefined();
  });
  it("取消关闭不保存、不关闭、不覆盖草稿", async () => {
    await open();
    await title().setValue("本地内容");
    await button("关闭问卷").trigger("click");
    expect(wrapper.get('[aria-label="关闭问卷确认"]').text()).toContain(
      "先保存",
    );
    await button("取消").trigger("click");
    expect(request.mock.calls.filter((c) => c[1])).toHaveLength(0);
    expect((title().element as HTMLInputElement).value).toBe("本地内容");
  });
  it("有修改时先保存再关闭，关闭不重新GET覆盖内容", async () => {
    request.mockImplementation(async (_p, m, b: any) => {
      if (m === "PUT")
        return { ...structuredClone(initial), revision: 2, draft: b.draft };
      if (m === "PATCH") return { ok: true, survey: meta(3, "closed") };
      return structuredClone(initial);
    });
    await open();
    await title().setValue("关闭前保存");
    await button("关闭问卷").trigger("click");
    await button("保存草稿并关闭").trigger("click");
    await flushPromises();
    expect(request.mock.calls.filter((c) => c[1]).map((c) => c[1])).toEqual([
      "PUT",
      "PATCH",
    ]);
    expect(request.mock.calls.find((c) => c[1] === "PATCH")?.[2]).toMatchObject(
      { revision: 2 },
    );
    expect(request.mock.calls.filter((c) => !c[1])).toHaveLength(1);
    expect((title().element as HTMLInputElement).value).toBe("关闭前保存");
    expect(wrapper.text()).toContain("问卷已关闭");
  });
  it("关闭前保存失败，不发送关闭请求", async () => {
    request.mockImplementation(async (_p, m) => {
      if (m === "PUT") throw Error("保存失败");
      return structuredClone(initial);
    });
    await open();
    await title().setValue("保留");
    await button("关闭问卷").trigger("click");
    await button("保存草稿并关闭").trigger("click");
    await flushPromises();
    expect(request.mock.calls.some((c) => c[1] === "PATCH")).toBe(false);
    expect((title().element as HTMLInputElement).value).toBe("保留");
    expect(wrapper.text()).toContain("保存失败");
  });
  it("关闭前保存期间又编辑时中止关闭，保留新增输入", async () => {
    const save = deferred();
    request.mockImplementation(async (_p, m) =>
      m === "PUT" ? save.promise : structuredClone(initial),
    );
    await open();
    await title().setValue("快照");
    await button("关闭问卷").trigger("click");
    await button("保存草稿并关闭").trigger("click");
    await title().setValue("新增输入");
    save.resolve({
      ...structuredClone(initial),
      revision: 2,
      draft: { ...structuredClone(initial.draft), title: "快照" },
    });
    await flushPromises();
    expect(request.mock.calls.some((c) => c[1] === "PATCH")).toBe(false);
    expect(wrapper.text()).toContain("本次未关闭");
    expect((title().element as HTMLInputElement).value).toBe("新增输入");
  });
  it("关闭请求期间输入仍保留，关闭失败也不覆盖", async () => {
    const patch = deferred();
    request.mockImplementation(async (_p, m) =>
      m === "PATCH" ? patch.promise : structuredClone(initial),
    );
    await open();
    await button("关闭问卷").trigger("click");
    await button("确认关闭").trigger("click");
    await title().setValue("关闭等待期间输入");
    patch.reject(Error("关闭请求失败"));
    await flushPromises();
    expect((title().element as HTMLInputElement).value).toBe(
      "关闭等待期间输入",
    );
    expect(wrapper.text()).toContain("关闭请求失败");
    expect(wrapper.text()).toContain("有未保存的草稿修改");
  });
  it("截止时间单独标记待发布，保存草稿不能假装已保存该时间", async () => {
    request.mockImplementation(async (_p, m, b: any) =>
      m === "PUT"
        ? { ...structuredClone(initial), revision: 2, draft: b.draft }
        : structuredClone(initial),
    );
    await open();
    await deadline().setValue("2030-01-01T12:30");
    expect(wrapper.text()).toContain("截止时间尚未发布");
    await button("保存草稿").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("发布新版本后生效");
    expect((deadline().element as HTMLInputElement).value).toBe(
      "2030-01-01T12:30",
    );
    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    vi.mocked(window.confirm).mockReturnValue(false);
    await router.push("/outside");
    expect(router.currentRoute.value.path).toBe("/surveys/survey/edit");
  });
  it("发布失败保留截止时间的待发布状态", async () => {
    request.mockImplementation(async (_p, m) => {
      if (m === "POST") throw Error("发布失败");
      return structuredClone(initial);
    });
    await open();
    await deadline().setValue("2030-01-01T12:30");
    await button("发布新版本 ↗").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("发布失败");
    expect(wrapper.text()).toContain("截止时间尚未发布");
  });
  it("发布等待期间的新草稿和时间不被响应覆盖", async () => {
    const publish = deferred();
    request.mockImplementation(async (_p, m) =>
      m === "POST" ? publish.promise : structuredClone(initial),
    );
    await open();
    await deadline().setValue("2030-01-01T12:30");
    await button("发布新版本 ↗").trigger("click");
    await title().setValue("发布期间新增");
    await deadline().setValue("2031-01-01T12:30");
    publish.resolve({
      version: 2,
      survey: meta(2, "published", new Date("2030-01-01T12:30").toISOString()),
    });
    await flushPromises();
    expect((title().element as HTMLInputElement).value).toBe("发布期间新增");
    expect((deadline().element as HTMLInputElement).value).toBe(
      "2031-01-01T12:30",
    );
    expect(wrapper.text()).toContain("截止时间尚未发布");
    expect(wrapper.text()).toContain("有未保存的草稿修改");
  });
  it("发布前保存期间新增输入，中止发布", async () => {
    const save = deferred();
    request.mockImplementation(async (_p, m) =>
      m === "PUT" ? save.promise : structuredClone(initial),
    );
    await open();
    await title().setValue("本次快照");
    await button("发布新版本 ↗").trigger("click");
    await title().setValue("新的内容");
    save.resolve({
      ...structuredClone(initial),
      revision: 2,
      draft: { ...structuredClone(initial.draft), title: "本次快照" },
    });
    await flushPromises();
    expect(request.mock.calls.some((c) => c[1] === "POST")).toBe(false);
    expect(wrapper.text()).toContain("本次未发布");
  });
  it("有进行中的保存时，禁止重复操作和路由离开", async () => {
    const save = deferred();
    request.mockImplementation(async (_p, m) =>
      m === "PUT" ? save.promise : structuredClone(initial),
    );
    await open();
    await title().setValue("保存中");
    await button("保存草稿").trigger("click");
    expect(button("发布新版本 ↗").attributes("disabled")).toBeDefined();
    expect(button("关闭问卷").attributes("disabled")).toBeDefined();
    await router.push("/outside");
    expect(router.currentRoute.value.path).toBe("/surveys/survey/edit");
    save.resolve({ ...structuredClone(initial), revision: 2 });
    await flushPromises();
  });
  it("损坏JSON拒绝应用，原配置与编辑器保持可用", async () => {
    await open();
    await button("高级：编辑组合条件 JSON").trigger("click");
    await wrapper
      .get('textarea[aria-label="跳转规则 JSON"]')
      .setValue('{"rules":[{}],"default_target":null}');
    await button("应用配置").trigger("click");
    expect(wrapper.text()).toContain("配置未应用");
    expect(wrapper.find('[aria-label="编辑组合条件"]').exists()).toBe(true);
    await button("取消").trigger("click");
    expect(wrapper.text()).not.toContain("配置损坏");
    expect(title().exists()).toBe(true);
  });
  it("关闭请求成功也保留等待期间的新输入", async () => {
    const patch = deferred();
    request.mockImplementation(async (_p, m) =>
      m === "PATCH" ? patch.promise : structuredClone(initial),
    );
    await open();
    await button("关闭问卷").trigger("click");
    await button("确认关闭").trigger("click");
    await title().setValue("关闭期间的新草稿");
    patch.resolve({ ok: true, survey: meta(2, "closed") });
    await flushPromises();
    expect((title().element as HTMLInputElement).value).toBe(
      "关闭期间的新草稿",
    );
    expect(wrapper.text()).toContain("有未保存的草稿修改");
    expect(wrapper.text()).toContain("问卷已关闭");
  });
  it("草稿已保存但关闭失败时保留成功保存的信息", async () => {
    request.mockImplementation(async (_p, m, b: any) => {
      if (m === "PUT")
        return { ...structuredClone(initial), revision: 2, draft: b.draft };
      if (m === "PATCH") throw Error("版本冲突");
      return structuredClone(initial);
    });
    await open();
    await title().setValue("已保存草稿");
    await button("关闭问卷").trigger("click");
    await button("保存草稿并关闭").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("草稿已保存，但关闭失败");
    expect(wrapper.text()).toContain("草稿已同步");
    expect((title().element as HTMLInputElement).value).toBe("已保存草稿");
  });
  it("截止时间未发布时关闭有明确确认，成功后仍保留待发布状态", async () => {
    request.mockImplementation(async (_p, m) =>
      m === "PATCH"
        ? { ok: true, survey: meta(2, "closed") }
        : structuredClone(initial),
    );
    await open();
    await deadline().setValue("2030-01-01T12:30");
    await button("关闭问卷").trigger("click");
    expect(wrapper.get('[aria-label="关闭问卷确认"]').text()).toContain(
      "关闭不会使其生效",
    );
    await button("确认关闭").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("截止时间尚未发布");
    expect((deadline().element as HTMLInputElement).value).toBe(
      "2030-01-01T12:30",
    );
    expect(request.mock.calls.some((c) => c[1] === "POST")).toBe(false);
  });
  it("成功发布清除本次截止时间标记，无新修改即可离开", async () => {
    request.mockImplementation(async (_p, m, b: any) =>
      m === "POST"
        ? { version: 2, survey: meta(2, "published", b.deadline) }
        : structuredClone(initial),
    );
    await open();
    await deadline().setValue("2030-01-01T12:30");
    await button("发布新版本 ↗").trigger("click");
    await flushPromises();
    expect(wrapper.text()).not.toContain("截止时间尚未发布");
    expect(wrapper.text()).toContain("已发布 v2");
    vi.mocked(window.confirm).mockClear();
    await router.push("/outside");
    expect(router.currentRoute.value.path).toBe("/outside");
    expect(window.confirm).not.toHaveBeenCalled();
  });
  it("未修改截止时间时发布保留服务器秒级精度", async () => {
    const old = {
      ...structuredClone(initial),
      deadline: "2030-01-01T12:30:45.123Z",
    };
    request.mockImplementation(async (_p, m, b: any) =>
      m === "POST"
        ? { version: 2, survey: meta(2, "published", b.deadline) }
        : old,
    );
    await open();
    await button("发布新版本 ↗").trigger("click");
    await flushPromises();
    expect(request.mock.calls.find((c) => c[1] === "POST")?.[2]).toMatchObject({
      deadline: old.deadline,
    });
  });
});
