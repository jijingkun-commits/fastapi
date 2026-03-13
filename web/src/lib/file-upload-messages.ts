export const LEGACY_DOC_CONVERT_HINT = "暂不支持 .doc，请先转换为 .docx";

export const SUPPORTED_IMAGE_UPLOAD_TYPES = [
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
] as const;

export const SUPPORTED_DOCUMENT_UPLOAD_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/csv",
  "text/plain",
  "text/markdown",
] as const;

export const SUPPORTED_UPLOAD_FILE_EXTENSIONS = [
  "jpg",
  "jpeg",
  "png",
  "gif",
  "webp",
  "pdf",
  "xlsx",
  "xls",
  "csv",
  "txt",
  "md",
  "docx",
] as const;

export const CHAT_FILE_INPUT_ACCEPT = [
  ...SUPPORTED_IMAGE_UPLOAD_TYPES,
  "application/pdf",
  ".xlsx",
  ".xls",
  ".csv",
  ".txt",
  ".md",
  ".docx",
].join(",");

export function isLegacyWordDocFile(file: Pick<File, "name" | "type">): boolean {
  const ext = file.name.split(".").pop()?.toLowerCase();
  return file.type === "application/msword" || ext === "doc";
}

export function isSupportedUploadFile(file: Pick<File, "name" | "type">): boolean {
  const ext = file.name.split(".").pop()?.toLowerCase();
  return (
    [...SUPPORTED_IMAGE_UPLOAD_TYPES, ...SUPPORTED_DOCUMENT_UPLOAD_TYPES].includes(
      file.type as (typeof SUPPORTED_IMAGE_UPLOAD_TYPES)[number] | (typeof SUPPORTED_DOCUMENT_UPLOAD_TYPES)[number],
    ) || !!(ext && SUPPORTED_UPLOAD_FILE_EXTENSIONS.includes(ext as (typeof SUPPORTED_UPLOAD_FILE_EXTENSIONS)[number]))
  );
}

export function buildUnsupportedFileNameMessage(fileName: string): string {
  return `不支持的文件类型：${fileName}`;
}

export function buildUnsupportedMimeTypeMessage(mimeType: string): string {
  return `不支持的文件类型：${mimeType}`;
}
