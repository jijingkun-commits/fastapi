import { ContentBlock } from "@langchain/core/messages";
import { toast } from "sonner";
import {
  LEGACY_DOC_CONVERT_HINT,
  buildUnsupportedFileNameMessage,
  buildUnsupportedMimeTypeMessage,
  isLegacyWordDocFile,
  isSupportedUploadFile,
} from "./file-upload-messages";

// 扩展 ContentBlock 以包含原始文件对象
export type ExtendedContentBlock = ContentBlock.Multimodal.Data & {
  file: File;
  previewUrl?: string;
};

// Returns a Promise of a typed multimodal block
export async function fileToContentBlock(
  file: File,
): Promise<ExtendedContentBlock> {
  if (isLegacyWordDocFile(file)) {
    toast.error(LEGACY_DOC_CONVERT_HINT);
    return Promise.reject(new Error(LEGACY_DOC_CONVERT_HINT));
  }

  if (!isSupportedUploadFile(file)) {
    toast.error(buildUnsupportedFileNameMessage(file.name));
    return Promise.reject(new Error(buildUnsupportedMimeTypeMessage(file.type)));
  }

  // 对于图片，生成预览 URL
  let previewUrl: string | undefined = undefined;
  if (file.type.startsWith("image/")) {
    previewUrl = URL.createObjectURL(file);
  }

  // 基础结构
  const block: ExtendedContentBlock = {
    type: file.type.startsWith("image/") ? "image" : "file",
    mimeType: file.type || "application/octet-stream",
    data: previewUrl || "", // 仅图片有 data (作为预览)，其他为空
    metadata: { name: file.name, size: file.size },
    file: file, // 保存原始文件对象
    previewUrl,
  };

  return block;
}

// Helper to convert File to base64 string (Legacy or specialized use only)
export async function fileToBase64(file: File): Promise<string> {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result as string;
      // Remove the data:...;base64, prefix
      resolve(result.split(",")[1]);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// Type guard for Base64ContentBlock
export function isBase64ContentBlock(
  block: unknown,
): block is ContentBlock.Multimodal.Data {
  if (typeof block !== "object" || block === null || !("type" in block))
    return false;
  return true;
}
