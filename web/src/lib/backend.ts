/**
 * 后端请求封装（中文注释）。
 *
 * 设计约定：
 * - `API_BASE` 统一决定后端地址，默认拼接当前主机的 8000 端口，可通过 `NEXT_PUBLIC_API_BASE_URL` 覆盖。
 * - `apiFetch(path, init, options)` 为统一的请求入口：
 *   - 默认自动从 `localStorage` 读取 `auth:token` 并添加 `Authorization` 头；
 *   - 传 `options.auth=false` 可禁用认证注入（如登录接口）。
 *   - 若调用方已手动设置 `Authorization`，则不再覆盖。
 * - 其他具体接口方法（如 `login`/`getMe`/`streamLLM`）均基于 `apiFetch` 构建，避免重复拼接头与地址。
 */
const DEFAULT_BASE =
  typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://localhost:8000";
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_BASE;

export async function apiFetch(
  path: string,
  init: RequestInit = {},
  options?: { auth?: boolean; handle401?: boolean },
) {
  const addAuth = options?.auth !== false;
  const handle401 = options?.handle401 !== false;
  // 使用 sessionStorage 存储 token，会话级别安全性更高（关闭浏览器自动清除）
  const token = typeof window !== "undefined" ? window.sessionStorage.getItem("auth:token") : null;
  const baseHeaders = init.headers ?? {};
  const hasAuth = typeof baseHeaders === "object" && baseHeaders !== null && "Authorization" in (baseHeaders as any);
  const authHeader = addAuth && !hasAuth && token ? { Authorization: `Bearer ${token}` } : {};
  const headers = { ...(baseHeaders as any), ...authHeader };
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });

  // 处理 401 未认证响应：清除 token 并跳转登录页
  if (response.status === 401 && handle401) {
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem("auth:token");
      window.location.href = "/auth";
    }
  }

  return response;
}

/** 登录接口：用户名或手机号 + 密码，禁止自动注入认证头 */
export async function login(payload: { username?: string; mobile?: string; password: string }) {
  const r = await apiFetch(`/api/v1/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }, { auth: false });
  if (!r.ok) throw new Error("login failed");
  return r.json();
}

/**
 * 附件模型
 */
export interface Attachment {
  name: string;
  url: string;
  mime_type: string;
  size: number;
  object_key: string;
}

/**
 * 获取当前用户信息：
 * - 若显式传入 `token`，使用该令牌；
 * - 否则自动走默认的 `apiFetch` 注入逻辑。
 */
export async function getMe(token?: string) {
  const r = await apiFetch(`/api/v1/me`, token ? { headers: { Authorization: `Bearer ${token}` } } : {});
  if (!r.ok) throw new Error("me failed");
  return r.json();
}

/**
 * 模型信息接口（后端返回）
 */
export interface ModelInfo {
  model_code: string;
  model_name: string;
  model_type: string;
  provider: string;
  supports_thinking: boolean;
  is_default: boolean;
}

/**
 * 获取可用模型列表（从后端 API）
 */
export async function getModels(): Promise<ModelInfo[]> {
  const r = await apiFetch(`/api/v1/llm/models`);
  if (!r.ok) throw new Error("获取模型列表失败");
  return r.json();
}

/**
 * 上传文件到后端
 * 
 * @param file 文件对象
 * @param threadId 可选的对话 ID（用于组织存储路径）
 * @returns 返回代理 URL 等信息
 */
export async function uploadFile(
  file: File,
  threadId?: string,
): Promise<{
  url: string;
  object_key: string;
  file_name: string;
  content_type: string;
  size: number;
}> {
  const formData = new FormData();
  formData.append("file", file);
  if (threadId) {
    formData.append("thread_id", threadId);
  }

  const r = await apiFetch(`/api/v1/upload`, {
    method: "POST",
    body: formData,
  });

  if (!r.ok) {
    const errorData = await r.json().catch(() => ({ detail: "上传失败" }));
    throw new Error(errorData.detail || "上传失败");
  }

  return r.json();
}



/**
 * SSE 事件回调接口
 */
export interface StreamCallbacks {
  /** 收到文本 Token */
  onToken?: (token: string) => void;
  /** 收到思考内容（Qwen Think 模式） */
  onThinking?: (content: string) => void;
  /** 工具开始调用 */
  onToolStart?: (name: string, input: any) => void;
  /** 工具调用结束 */
  onToolEnd?: (name: string, output: string) => void;
  /** 流初始化（返回 thread_id） */
  onInit?: (threadId: string) => void;
  /** 流结束 */
  onDone?: (threadId?: string, additionalKwargs?: Record<string, unknown>) => void;
  /** 错误 */
  onError?: (message: string) => void;
  /** 需要人工审核（interrupt） */
  onInterrupt?: (data: InterruptData) => void;
  /** 结构化结果（待办列表、图片等） */
  onResult?: (data: { data_type: string; data: any; message?: string }) => void;
  /** 状态更新 */
  onStatus?: (message: string) => void;
  /** 澄清问题 */
  onClarification?: (data: { questions: string[]; message?: string }) => void;
  /** 知识库图片映射（用于替换占位符） */
  onKbImages?: (images: Record<string, string>) => void;
}

/**
 * Interrupt 数据类型
 */
export interface InterruptData {
  thread_id: string;
  interrupt_id: string;
  value: {
    action_requests?: Array<{
      name: string;
      args: Record<string, unknown>;
      description?: string;
    }>;
    review_configs?: Array<{
      action_name: string;
      allowed_decisions: string[];
    }>;
    message?: string;
  };
}

/**
 * 用户决定类型
 */
export type DecisionType =
  | { type: "accept" }
  | { type: "reject"; message?: string }
  | { type: "edit"; args: Record<string, unknown> };

/**
 * SSE 流式接口（升级版）：支持多种事件类型
 * 
 * 事件类型：
 * - init: 初始化，包含 thread_id
 * - token: AI 文字输出
 * - thinking: Qwen Think 模式的思考过程
 * - tool_start: 开始调用工具
 * - tool_end: 工具调用结束
 * - done: 流结束
 * - error: 错误信息
 */
export async function streamLLM(
  prompt: string,
  callbacks: StreamCallbacks | ((token: string) => void),
  options?: {
    modelId?: string;
    aiConfigId?: string;
    threadId?: string;
    enableThinking?: boolean;
    attachments?: Attachment[];
    currentTodoId?: number;
    idempotencyKey?: string;
    signal?: AbortSignal;
  },
) {
  const cb =
    typeof callbacks === "function" ? { onToken: callbacks } : callbacks;
  const { onToken, onThinking, onToolStart, onToolEnd, onInit, onDone, onError, onInterrupt, onResult, onStatus, onClarification, onKbImages } = cb;

  // 构建请求头：幂等键通过 Header 传递
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (options?.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }

  // 注意：use_multi_agent 已废弃（2026-01-31），后端默认使用多智能体模式
  const response = await apiFetch(`/api/v1/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      prompt,
      model_id: options?.modelId,
      thread_id: options?.threadId,
      enable_thinking: options?.enableThinking,
      attachments: options?.attachments,
      current_todo_id: options?.currentTodoId,
    }),
    signal: options?.signal,
  });

  if (!response.ok) {
    throw new Error(response.statusText);
  }

  // ... (Stream processing logic)
  const reader = response.body?.getReader();
  if (!reader) {
    onDone?.(options?.threadId);
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let doneCalled = false;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      // Keep the last partial line in the buffer
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("event: ")) continue;

        const typeMatch = line.match(/^event: (.+)$/m);
        if (!typeMatch) continue;
        const type = typeMatch[1].trim();

        const parts = line.split("\n");
        let dataStr = "";
        for (const part of parts) {
          if (part.startsWith("data: ")) {
            dataStr = part.substring(6);
            break;
          }
        }

        if (!dataStr) continue;

        try {
          const data = JSON.parse(dataStr);

          // ... (event handling)
          if (type === "init") {
            onInit?.(data.thread_id);
          } else if (type === "token") {
            if (data.reasoning_content && onThinking) {
              onThinking(data.reasoning_content);
            }
            if (data.content && onToken) {
              onToken(data.content);
            }
          } else if (type === "thinking") { // Added thinking event handling
            onThinking?.(data.content);
          } else if (type === "tool_start") {
            onToolStart?.(data.name, data.input);
          } else if (type === "tool_end") {
            onToolEnd?.(data.name, data.output);
          } else if (type === "interrupt") {
            onInterrupt?.(data as InterruptData);
          } else if (type === "result") {
            // 结构化结果事件
            onResult?.(data);
          } else if (type === "status") {
            // 状态更新事件
            onStatus?.(data.message);
          } else if (type === "clarification") {
            // 澄清问题事件
            onClarification?.(data);
          } else if (type === "kb_images") {
            // 知识库图片映射事件
            onKbImages?.(data.images);
          } else if (type === "done") {
            if (!doneCalled) {
              doneCalled = true;
              onDone?.(data.thread_id, data.additional_kwargs);
            }
          } else if (type === "error") {
            onError?.(data.message);
          }
        } catch (e) {
          console.error("JSON parse error", e);
        }
      }
    }
  } catch (err: any) {
    if (err.name === 'AbortError') {
      // aborted
    } else {
      onError?.(err.message || "Stream error");
    }
  } finally {
    // 确保在正常结束或异常时调用 onDone，避免状态卡死
    // 使用 doneCalled 标记防止重复调用
    if (!doneCalled) {
      doneCalled = true;
      onDone?.(options?.threadId);
    }
  }
}

// SSE 流超时时间（毫秒）
const SSE_TIMEOUT_MS = 120_000; // 2 分钟

export function startLLMStream(
  prompt: string,
  callbacks: StreamCallbacks | ((token: string) => void),
  maxTokens: number = 50,
  threadId?: string,
  enableThinking: boolean = false,
  modelId?: string,
  attachments?: Attachment[],
  currentTodoId?: number,
  idempotencyKey?: string,
  timeoutMs: number = SSE_TIMEOUT_MS,
) {
  const ctrl = new AbortController();
  
  // 设置超时自动取消
  const timeoutId = setTimeout(() => {
    ctrl.abort();
    const cb = typeof callbacks === "function" ? { onError: undefined } : callbacks;
    cb.onError?.("请求超时，请重试");
  }, timeoutMs);
  
  const promise = streamLLM(prompt, callbacks, {
    modelId,
    threadId,
    enableThinking,
    attachments,
    currentTodoId,
    idempotencyKey,
    signal: ctrl.signal,
  }).finally(() => {
    clearTimeout(timeoutId);
  });

  return {
    stop: () => {
      clearTimeout(timeoutId);
      ctrl.abort();
    },
    promise,
  };
}

/**
 * 恢复被中断的流程
 */
export async function resumeChat(
  threadId: string,
  decision: DecisionType,
  callbacks: StreamCallbacks,
  options?: { delay_ms?: number; signal?: AbortSignal },
) {
  const r = await apiFetch(`/api/v1/chat/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      thread_id: threadId,
      decision,
      delay_ms: options?.delay_ms ?? 0,
    }),
    signal: options?.signal,
  });
  if (!r.ok || !r.body) throw new Error("resume failed");

  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        const data = line.slice(6);
        try {
          const obj = JSON.parse(data);

          switch (currentEvent) {
            case "token":
              callbacks.onToken?.(obj.content);
              break;
            case "thinking":
              callbacks.onThinking?.(obj.content);
              break;
            case "tool_start":
              callbacks.onToolStart?.(obj.name, obj.input);
              break;
            case "tool_end":
              callbacks.onToolEnd?.(obj.name, obj.output);
              break;

            case "done":
              callbacks.onDone?.(obj.thread_id);
              break;
            case "error":
              callbacks.onError?.(obj.message);
              break;
            case "interrupt":
              callbacks.onInterrupt?.(obj as InterruptData);
              break;
          }
        } catch {
          // 忽略解析错误
        }
        currentEvent = "";
      }
    }
  }
}

/**
 * 启动 resume 流（带中止控制）
 */
export function startResumeStream(
  threadId: string,
  decision: DecisionType,
  callbacks: StreamCallbacks,
  delay_ms = 0,
) {
  const ctrl = new AbortController();
  const promise = resumeChat(threadId, decision, callbacks, { delay_ms, signal: ctrl.signal });
  return {
    stop: () => ctrl.abort(),
    promise,
  };
}

// ==================== 历史消息 API ====================

/**
 * 对话线程类型
 */
export interface ConversationThread {
  thread_id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * 消息类型
 */
export interface ConversationMessage {
  id: number;
  thread_id: string;
  role: "human" | "ai";
  content_type: "text" | "markdown" | "mixed" | "multimodal";
  content: string | ContentBlock[];
  metadata?: Record<string, any>;
  created_at?: string;
}

export interface ContentBlock {
  type: "markdown" | "text" | "chart" | "image" | "custom_ui";
  data: any;
  component?: string;
  props?: Record<string, any>;
}

/**
 * 获取用户的对话列表
 */
export async function getThreads(userId: number, limit = 50): Promise<ConversationThread[]> {
  const r = await apiFetch(`/api/v1/chat/threads?user_id=${userId}&limit=${limit}`);
  if (!r.ok) throw new Error("获取对话列表失败");
  return r.json();
}

/**
 * 获取指定对话的消息历史
 */
export async function getThreadMessages(threadId: string, limit = 100): Promise<ConversationMessage[]> {
  const r = await apiFetch(`/api/v1/chat/threads/${threadId}/messages?limit=${limit}`);
  if (!r.ok) throw new Error("获取消息历史失败");
  return r.json();
}

/**
 * 删除对话线程
 */
export async function deleteThread(threadId: string, userId?: number): Promise<void> {
  const url = userId
    ? `/api/v1/chat/threads/${threadId}?user_id=${userId}`
    : `/api/v1/chat/threads/${threadId}`;
  const r = await apiFetch(url, { method: "DELETE" });
  if (!r.ok) throw new Error("删除对话失败");
}

/**
 * 提交消息反馈
 */
export async function submitFeedback(
  messageId: number | string,
  score: number, // 1: Like, -1: Dislike, 0: Cancel
  reason?: string
): Promise<void> {
  const r = await apiFetch(`/api/v1/chat/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message_id: messageId,
      score,
      reason,
    }),
  });
  if (!r.ok) throw new Error("提交反馈失败");
}

/**
 * 批量删除对话线程
 */
export async function deleteThreadsBatch(threadIds: string[]): Promise<{
  message: string;
  stats: {
    total_messages: number;
    total_assets: number;
    total_minio: number;
    threads_deleted: number;
  };
}> {
  const r = await apiFetch(`/api/v1/chat/threads/batch`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_ids: threadIds }),
  });
  if (!r.ok) throw new Error("批量删除对话失败");
  return r.json();
}

// ==================== 用户管理 API ====================

/**
 * 用户列表项
 */
export interface UserListItem {
  id: number;
  username: string | null;
  mobile: string | null;
  role: string | null;
  org_code: string | null;
  org_name: string | null;
  dept_code: string | null;
  dept_name: string | null;
  is_active: boolean;
  create_time: string | null;
}

/**
 * 用户列表响应
 */
export interface UserListResponse {
  items: UserListItem[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * 创建用户请求
 */
export interface CreateUserRequest {
  username: string;
  password: string;
  mobile?: string;
  role?: "user" | "analyst" | "admin";
  org_code?: string;
  org_name?: string;
  dept_code?: string;
  dept_name?: string;
}

/**
 * 获取用户列表（管理员）
 */
export async function listUsers(
  page: number = 1,
  pageSize: number = 20,
  search?: string
): Promise<UserListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (search) params.append("search", search);
  
  const r = await apiFetch(`/api/v1/users?${params}`);
  if (!r.ok) throw new Error("获取用户列表失败");
  return r.json();
}/**
 * 创建用户（管理员）
 */
export async function createUser(data: CreateUserRequest): Promise<UserListItem> {
  const r = await apiFetch(`/api/v1/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: "创建用户失败" }));
    throw new Error(err.detail || "创建用户失败");
  }
  return r.json();
}

/**
 * 更新用户状态（管理员）
 */
export async function updateUserStatus(
  userId: number,
  isActive: boolean
): Promise<UserListItem> {
  const r = await apiFetch(`/api/v1/users/${userId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: isActive }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: "更新状态失败" }));
    throw new Error(err.detail || "更新状态失败");
  }
  return r.json();
}/**
 * 用户登出
 */
export async function logout(): Promise<void> {
  const r = await apiFetch(`/api/v1/logout`, {
    method: "POST",
  }, { handle401: false });
  // 不论服务端是否成功，都清除本地 token
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem("auth:token");
  }
}
