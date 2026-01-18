import type { Message } from "@langchain/langgraph-sdk";

/**
 * Extracts a string summary from a message's content, supporting multimodal (text, image, file, etc.).
 * - If text is present, returns the joined text.
 * - If not, returns a label for the first non-text modality (e.g., 'Image', 'Other').
 * - If unknown, returns 'Multimodal message'.
 */
export function getContentString(content: Message["content"]): string {
  if (typeof content === "string") return content;
  const texts = content
    .filter((c): c is { type: "text"; text: string } => c.type === "text")
    .map((c) => c.text);
  return texts.join(" ");
}

/**
 * 知识库图片映射类型
 */
export type KbImages = Record<string, string>;

/**
 * 将内容中的 [IMG-N] 占位符替换为实际的 Markdown 图片语法
 * @param content 包含占位符的内容
 * @param kbImages 图片映射 {索引: URL}
 * @returns 替换后的内容
 */
export function replaceImagePlaceholders(content: string, kbImages: KbImages): string {
  if (!kbImages || Object.keys(kbImages).length === 0) return content;

  let result = content;
  for (const [idx, url] of Object.entries(kbImages)) {
    const placeholder = `[IMG-${idx}]`;
    if (result.includes(placeholder)) {
      result = result.replace(placeholder, `![参考图片](${url})`);
    }
  }
  return result;
}
