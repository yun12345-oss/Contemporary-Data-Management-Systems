import { reactive } from "vue";
export const auth = reactive<{
  user: { id: string; username: string } | null;
  ready: boolean;
}>({ user: null, ready: false });
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details: any,
  ) {
    super(message);
  }
}
export async function api<T = any>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    credentials: "same-origin",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response
    .json()
    .catch(() => ({ error: "服务返回了无法读取的内容" }));
  if (!response.ok)
    throw new ApiError(data.error || "请求失败", response.status, data.details);
  return data;
}
export async function loadUser() {
  try {
    auth.user = await api("/auth/me");
  } catch {
    auth.user = null;
  } finally {
    auth.ready = true;
  }
}
