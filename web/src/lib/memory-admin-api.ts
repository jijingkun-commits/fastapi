/**
 * 记忆管理后台 API SDK。
 */

import { apiFetch } from "@/lib/backend";
import type {
  DocumentEmbeddingRebuildRequest,
  DocumentEmbeddingRebuildResponse,
  DocumentEmbeddingStatusParams,
  DocumentEmbeddingStatusResponse,
  DocumentRetryFailedRequest,
  MemoryArchiveResponse,
  MemoryChunkListParams,
  MemoryChunkListResponse,
  MemoryDeleteResponse,
  MemoryDetail,
  MemoryGovernanceActionParams,
  MemoryListParams,
  MemoryListResponse,
  MemoryOverviewResponse,
  MemorySearchDebugRequest,
  MemorySearchDebugResponse,
} from "@/types/memory-admin";

const API_BASE = "/api/v1/memory-admin";

function appendQueryValue(
  searchParams: URLSearchParams,
  key: string,
  value: string | number | boolean | null | undefined,
): void {
  if (value === undefined || value === null || value === "") {
    return;
  }

  searchParams.set(key, String(value));
}

function createQueryString(
  query: Record<string, string | number | boolean | null | undefined>,
): string {
  const searchParams = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    appendQueryValue(searchParams, key, value);
  });

  const serialized = searchParams.toString();
  return serialized ? `?${serialized}` : "";
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  const payload = await response.json().catch(() => null) as
    | { detail?: unknown; message?: unknown; error?: unknown }
    | null;
  if (typeof payload?.detail === "string" && payload.detail.trim()) {
    return payload.detail;
  }
  if (typeof payload?.message === "string" && payload.message.trim()) {
    return payload.message;
  }
  if (typeof payload?.error === "string" && payload.error.trim()) {
    return payload.error;
  }
  return fallback;
}

async function ensureOk(response: Response, fallback: string): Promise<void> {
  if (response.ok) {
    return;
  }
  throw new Error(await readErrorMessage(response, fallback));
}

export async function listMemories(params: MemoryListParams = {}): Promise<MemoryListResponse> {
  const query = createQueryString({
    user_id: params.user_id,
    doc_kind: params.doc_kind,
    status: params.status,
    source: params.source,
    keyword: params.keyword,
    updated_from: params.updated_from,
    updated_to: params.updated_to,
    page: params.page,
    page_size: params.page_size,
  });

  const response = await apiFetch(`${API_BASE}/memories${query}`);
  await ensureOk(response, "获取记忆列表失败");
  return response.json();
}

export async function getMemoryDetail(
  memoryId: number,
  params: Pick<MemoryChunkListParams, "user_id"> = {},
): Promise<MemoryDetail> {
  const query = createQueryString({ user_id: params.user_id });
  const response = await apiFetch(`${API_BASE}/memories/${memoryId}${query}`);
  await ensureOk(response, "获取记忆详情失败");
  return response.json();
}

export async function getMemoryChunks(
  memoryId: number,
  params: MemoryChunkListParams = {},
): Promise<MemoryChunkListResponse> {
  const query = createQueryString({
    user_id: params.user_id,
    embedding_status: params.embedding_status,
    page: params.page,
    page_size: params.page_size,
  });
  const response = await apiFetch(`${API_BASE}/memories/${memoryId}/chunks${query}`);
  await ensureOk(response, "获取记忆分块失败");
  return response.json();
}

export async function searchMemoryDebug(
  payload: MemorySearchDebugRequest,
): Promise<MemorySearchDebugResponse> {
  const response = await apiFetch(`${API_BASE}/memories/search-debug`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await ensureOk(response, "执行调试查询失败");
  return response.json();
}

export async function archiveMemory(
  memoryId: number,
  params: MemoryGovernanceActionParams = {},
): Promise<MemoryArchiveResponse> {
  const query = createQueryString({
    user_id: params.user_id,
    operator_id: params.operator_id,
  });
  const response = await apiFetch(`${API_BASE}/memories/${memoryId}/archive${query}`, {
    method: "POST",
  });
  await ensureOk(response, "归档记忆失败");
  return response.json();
}

export async function deleteMemory(
  memoryId: number,
  params: MemoryGovernanceActionParams = {},
): Promise<MemoryDeleteResponse> {
  const query = createQueryString({
    user_id: params.user_id,
    operator_id: params.operator_id,
  });
  const response = await apiFetch(`${API_BASE}/memories/${memoryId}${query}`, {
    method: "DELETE",
  });
  await ensureOk(response, "删除记忆失败");
  return response.json();
}

export async function rebuildDocumentEmbeddings(
  payload: DocumentEmbeddingRebuildRequest,
): Promise<DocumentEmbeddingRebuildResponse> {
  const response = await apiFetch(`${API_BASE}/document/rebuild-embeddings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await ensureOk(response, "触发向量重建失败");
  return response.json();
}

export async function retryFailedDocumentEmbeddings(
  payload: DocumentRetryFailedRequest,
): Promise<DocumentEmbeddingRebuildResponse> {
  const response = await apiFetch(`${API_BASE}/document/retry-failed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await ensureOk(response, "重试失败分块失败");
  return response.json();
}

export async function getDocumentEmbeddingStatus(
  params: DocumentEmbeddingStatusParams = {},
): Promise<DocumentEmbeddingStatusResponse> {
  const query = createQueryString({
    user_id: params.user_id,
    doc_id: params.doc_id,
    dimension: params.dimension,
    limit: params.limit,
    offset: params.offset,
  });
  const response = await apiFetch(`${API_BASE}/document/embedding-status${query}`);
  await ensureOk(response, "获取向量状态失败");
  return response.json();
}

export async function getMemoryOverview(topN: number = 10): Promise<MemoryOverviewResponse> {
  const query = createQueryString({ top_n: topN });
  const response = await apiFetch(`${API_BASE}/memory-overview${query}`);
  await ensureOk(response, "获取记忆总览失败");
  return response.json();
}
