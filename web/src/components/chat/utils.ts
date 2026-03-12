import type { Message } from "@langchain/langgraph-sdk";

/**
 * Extracts a string summary from a message's content, supporting multimodal (text, image, file, etc.).
 * - If text is present, returns the joined text.
 * - If not, returns a label for the first non-text modality (e.g., 'Image', 'Other').
 * - If unknown, returns 'Multimodal message'.
 */
export function getContentString(content: Message["content"]): string {
  if (typeof content === "string") return content;
  const texts = content.flatMap((item) => {
    const maybeText = item as { type?: string; text?: unknown; data?: unknown };
    if (maybeText.type === "text" && typeof maybeText.text === "string") {
      return [maybeText.text];
    }
    if ((maybeText.type === "markdown" || maybeText.type === "text") && typeof maybeText.data === "string") {
      return [maybeText.data];
    }
    if (
      (maybeText.type === "markdown" || maybeText.type === "text")
      && typeof maybeText.data === "object"
      && maybeText.data !== null
      && typeof (maybeText.data as { text?: unknown }).text === "string"
    ) {
      return [(maybeText.data as { text: string }).text];
    }
    return [];
  });
  return texts.join(" ");
}

/**
 * 知识库图片映射类型
 */
export type KbImages = Record<string, string>;
