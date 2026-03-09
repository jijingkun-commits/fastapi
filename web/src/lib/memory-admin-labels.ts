const MEMORY_STATUS_LABELS: Record<string, string> = {
  active: "启用",
  archived: "已归档",
  all: "全部",
  pending: "待处理",
  ready: "已就绪",
  failed: "失败",
};

const MEMORY_DOC_KIND_LABELS: Record<string, string> = {
  daily: "日常",
  preference: "偏好",
};

export function getMemoryStatusLabel(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return MEMORY_STATUS_LABELS[value] || value;
}

export function getMemoryDocKindLabel(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return MEMORY_DOC_KIND_LABELS[value] || value;
}
