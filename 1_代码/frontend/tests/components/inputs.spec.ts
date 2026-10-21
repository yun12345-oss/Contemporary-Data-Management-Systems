import { afterEach, describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import TextInput from "../../src/question-types/TextInput.vue";
import RoutingEditor from "../../src/components/RoutingEditor.vue";
import { validate } from "../../src/rules";
import { reactive } from "vue";
const q = {
  id: "q1",
  type: "text",
  title: "一个字符",
  required: true,
  options: [],
  validation: { max_length: 1 },
  routing: { rules: [], default_target: null },
};
const wrappers: any[] = [];
afterEach(() => {
  wrappers.splice(0).forEach((w) => w.unmount());
});
function text() {
  const w = mount(TextInput, {
    props: { question: structuredClone(q), modelValue: "" },
  });
  wrappers.push(w);
  return w;
}
describe("文本组件与后端的码点长度口径", () => {
  it("一个表情可实际输入，上限1时不使用UTF-16 maxlength", async () => {
    const w = text();
    const input = w.get("textarea");
    expect(input.attributes("maxlength")).toBeUndefined();
    await input.setValue("😀");
    expect((input.element as HTMLTextAreaElement).value).toBe("😀");
    expect(w.emitted("update:modelValue")?.at(-1)).toEqual(["😀"]);
    expect(w.text()).toContain("1 / 1");
    expect(w.find('[role="alert"]').exists()).toBe(false);
    expect(validate(q, "😀")).toBe("");
  });
  it("粘贴多个表情保留全文，显示超限且规则拒绝", async () => {
    const w = text();
    await w.get("textarea").setValue("😀😀");
    expect((w.get("textarea").element as HTMLTextAreaElement).value).toBe(
      "😀😀",
    );
    expect(w.text()).toContain("2 / 1");
    expect(w.get('[role="alert"]').text()).toContain("内容已保留");
    expect(validate(q, "😀😀")).not.toBe("");
  });
  it("中文组合输入结束前不提交中间内容，不提前提示超限", async () => {
    const w = text();
    const input = w.get("textarea");
    await input.trigger("compositionstart");
    (input.element as HTMLTextAreaElement).value = "zhong";
    await input.trigger("input", { isComposing: true });
    expect(w.emitted("update:modelValue")).toBeUndefined();
    expect(w.find('[role="alert"]').exists()).toBe(false);
    (input.element as HTMLTextAreaElement).value = "中";
    await input.trigger("compositionend");
    expect(w.emitted("update:modelValue")).toEqual([["中"]]);
    expect(w.text()).toContain("1 / 1");
  });
  it("组合结束后的重复input不重复发出更新，计数去除首尾空白", async () => {
    const w = text();
    const input = w.get("textarea");
    await input.trigger("compositionstart");
    (input.element as HTMLTextAreaElement).value = " 😀 ";
    await input.trigger("compositionend");
    await input.trigger("input");
    expect(w.emitted("update:modelValue")).toEqual([[" 😀 "]]);
    expect(w.text()).toContain("1 / 1");
  });
  it("外部模型更新可以清空实际输入", async () => {
    const w = text();
    await w.get("textarea").setValue("😀");
    await w.setProps({ modelValue: "新" });
    await w.setProps({ modelValue: "" });
    expect((w.get("textarea").element as HTMLTextAreaElement).value).toBe("");
    expect(w.text()).toContain("0 / 1");
  });
});
describe("规则组件防御性渲染", () => {
  for (const routing of [
    null,
    { rules: [{}], default_target: null },
    {
      rules: [
        {
          condition: { question_id: "q1", operator: "between", value: null },
          target: "END",
        },
      ],
      default_target: null,
    },
  ]) {
    it("损坏配置显示错误且可明确清空：" + JSON.stringify(routing), async () => {
      const question = reactive({ ...structuredClone(q), routing }) as any;
      const w = mount(RoutingEditor, {
        props: { question, questions: [question], index: 0 },
      });
      wrappers.push(w);
      expect(w.get('[role="alert"]').text()).toContain("跳转配置损坏");
      const clear = w
        .findAll("button")
        .find((b) => b.text() === "清空损坏的跳转配置")!;
      await clear.trigger("click");
      expect(question.routing).toEqual({ rules: [], default_target: null });
      expect(w.find('[role="alert"]').exists()).toBe(false);
    });
  }
});
