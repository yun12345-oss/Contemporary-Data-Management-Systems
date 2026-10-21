export interface Option {
  id: string;
  label: string;
}
export interface Condition {
  question_id?: string;
  operator?: string;
  value?: any;
  all?: Condition[];
  any?: Condition[];
}
export interface Rule {
  condition: Condition;
  target: string;
}
export interface Question {
  id: string;
  type: string;
  title: string;
  required: boolean;
  options: Option[];
  validation: Record<string, any>;
  routing: { rules: Rule[]; default_target: string | null };
}
export interface Definition {
  title: string;
  description: string;
  allow_anonymous: boolean;
  allow_repeat: boolean;
  questions: Question[];
}
export interface Survey {
  _id: string;
  share_code: string;
  status: string;
  revision: number;
  current_version: number;
  deadline: string | null;
  draft: Definition;
  created_at: string;
  updated_at: string;
  response_count?: number;
}
export const typeNames: Record<string, string> = {
  single_choice: "单选题",
  multiple_choice: "多选题",
  text: "文本填空",
  number: "数字填空",
};
export const makeId = (prefix = "q") =>
  `${prefix}_${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}`;
export function makeQuestion(type: string): Question {
  return {
    id: makeId(),
    type,
    title: "",
    required: true,
    options: ["single_choice", "multiple_choice"].includes(type)
      ? [
          { id: makeId("o"), label: "选项 1" },
          { id: makeId("o"), label: "选项 2" },
        ]
      : [],
    validation: {},
    routing: { rules: [], default_target: null },
  };
}
export const dateLabel = (value: string | null) =>
  value
    ? new Date(value).toLocaleString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "未设置";
