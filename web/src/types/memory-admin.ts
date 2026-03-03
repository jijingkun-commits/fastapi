/**
 * 记忆管理后台类型定义。
 */

export type MemoryDocumentStatus = "active" | "archived" | string;
export type MemoryEmbeddingStatus = "pending" | "ready" | "failed" | string;

export interface MemoryListParams {
  user_id?: number;
  doc_kind?: string;
  status?: string;
  source?: string;
  keyword?: string;
  updated_from?: string;
  updated_to?: string;
  page?: number;
  page_size?: number;
}

export interface MemoryListItem {
  memory_id: number;
  user_id: number;
  doc_kind: string;
  doc_key: string;
  title: string | null;
  summary_md: string | null;
  source: string;
  scope: string;
  scope_ref: string | null;
  status: MemoryDocumentStatus;
  revision: number;
  chunk_total: number;
  ready_chunks: number;
  failed_chunks: number;
  create_time: string | null;
  update_time: string | null;
}

export interface MemoryListResponse {
  items: MemoryListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface MemoryDetail {
  memory_id: number;
  user_id: number;
  doc_kind: string;
  doc_key: string;
  title: string | null;
  content_md: string;
  summary_md: string | null;
  source: string;
  scope: string;
  scope_ref: string | null;
  status: MemoryDocumentStatus;
  revision: number;
  source_thread_id: string | null;
  source_message_id: number | null;
  chunk_total: number;
  ready_chunks: number;
  failed_chunks: number;
  create_time: string | null;
  update_time: string | null;
}

export interface MemoryChunkListParams {
  user_id?: number;
  embedding_status?: string;
  page?: number;
  page_size?: number;
}

export interface MemoryChunkItem {
  chunk_id: number;
  doc_id: number;
  user_id: number;
  chunk_no: number;
  start_line: number;
  end_line: number;
  chunk_text: string;
  chunk_hash: string;
  embedding_status: MemoryEmbeddingStatus;
  embedding_retry_count: number;
  embedding_model: string | null;
  embedding_error: string | null;
  embedding_updated_time: string | null;
  source: string;
  create_time: string | null;
  update_time: string | null;
}

export interface MemoryChunkListResponse {
  memory_id: number;
  user_id: number;
  status: MemoryDocumentStatus;
  items: MemoryChunkItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface MemorySearchDebugRequest {
  user_id: number;
  query_text: string;
  max_results?: number;
  limit?: number;
  min_score?: number;
  vector_weight?: number;
  text_weight?: number;
}

export interface MemorySearchDebugItem {
  doc_id: number;
  doc_kind: string;
  doc_key: string;
  start_line: number;
  end_line: number;
  chunk_text: string;
  text_score: number;
  vector_score: number;
  score?: number;
  final_score: number;
  citation: string;
}

export interface MemorySearchDebugResponse {
  user_id: number;
  query_text: string;
  total: number;
  items: MemorySearchDebugItem[];
}

export interface MemoryArchiveResponse {
  memory_id: number;
  user_id?: number | null;
  operator_id?: number | null;
  status: string;
  found: boolean;
  changed: boolean;
}

export interface MemoryDeleteResponse {
  memory_id: number;
  user_id?: number | null;
  operator_id?: number | null;
  status: string;
  found: boolean;
  deleted: boolean;
  deleted_chunks: number;
}

export interface MemoryGovernanceActionParams {
  user_id?: number;
  operator_id?: number;
}

export interface DocumentEmbeddingRebuildRequest {
  user_id?: number;
  doc_id?: number;
  status_filter?: string[];
  limit?: number;
  run_async?: boolean;
}

export interface DocumentRetryFailedRequest {
  user_id?: number;
  doc_id?: number;
  limit?: number;
  run_async?: boolean;
}

export interface DocumentEmbeddingRebuildResponse {
  status: string;
  total: number;
  processed: number;
  ready: number;
  failed: number;
  reset: number;
  elapsed_ms: number;
}

export interface EmbeddingStatusSummary {
  total: number;
  pending: number;
  ready: number;
  failed: number;
}

export interface EmbeddingStatusGroupItem extends EmbeddingStatusSummary {
  user_id?: number | null;
  doc_id?: number | null;
  doc_kind?: string | null;
  doc_key?: string | null;
  title?: string | null;
  document_total?: number | null;
}

export interface DocumentEmbeddingStatusParams {
  user_id?: number;
  doc_id?: number;
  dimension?: "user" | "doc";
  limit?: number;
  offset?: number;
}

export interface DocumentEmbeddingStatusResponse extends EmbeddingStatusSummary {
  dimension?: "user" | "doc";
  limit?: number;
  offset?: number;
  group_total?: number;
  groups?: EmbeddingStatusGroupItem[];
}

export interface MemoryOverviewTotals {
  users: number;
  documents: number;
  chunks: number;
}

export interface MemoryOverviewResponse {
  totals: MemoryOverviewTotals;
  embedding_status: EmbeddingStatusSummary;
  top_users: EmbeddingStatusGroupItem[];
  top_documents: EmbeddingStatusGroupItem[];
}
