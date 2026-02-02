import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { z, ZodSchema } from "zod";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * 安全解析 JSON 并使用 Zod 校验结构
 * @param json - JSON 字符串
 * @param schema - Zod 校验模式
 * @param fallback - 解析失败时的默认值
 * @returns 解析后的数据或默认值
 */
export function safeParseJson<T>(
  json: string | null | undefined,
  schema: ZodSchema<T>,
  fallback: T
): T {
  if (!json) return fallback;
  try {
    const parsed = JSON.parse(json);
    const result = schema.safeParse(parsed);
    if (result.success) {
      return result.data;
    }
    console.warn("JSON 结构校验失败:", result.error.message);
    return fallback;
  } catch (e) {
    console.warn("JSON 解析失败:", e);
    return fallback;
  }
}

// 常用的 sessionStorage 数据模式
export const SelectedTodoSchema = z.object({
  id: z.number(),
  title: z.string(),
  threadId: z.string().optional(),
});
