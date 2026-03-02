/**
 * 技能管理 API 客户端（中文注释）
 *
 * 提供：
 * - 技能列表查询
 * - 向量状态检查
 * - 向量重新生成
 */

import { apiFetch } from '@/lib/backend';

const API_BASE = '/api/v1/skill-admin';
const DEFAULT_SKILL_PAGE_SIZE = 200;
const MAX_SKILL_FETCH_PAGES = 100;

// ==================== 类型定义 ====================

export interface Skill {
  id: number;
  skill_id: string;
  name: string;
  description: string | null;
  content_preview: string;
  file_hash: string | null;
  has_embedding: boolean;
  embedding_dim: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface SkillDetail {
  id: number;
  skill_id: string;
  name: string;
  description: string | null;
  content: string;
  file_hash: string | null;
  has_embedding: boolean;
  embedding_dim: number | null;
}

export interface VectorStatus {
  total_skills: number;
  with_embedding: number;
  without_embedding: number;
  embedding_dim: number | null;
  dimension_mismatch: boolean;
  current_model_dim: number | null;
}

export interface SearchResult {
  skill_id: string;
  name: string;
  description: string | null;
  similarity: number;
}

export interface SkillListParams {
  search?: string;
  has_embedding?: boolean;
}

export interface SkillPageParams extends SkillListParams {
  skip?: number;
  limit?: number;
}

export interface BootstrapTemplateSkill {
  skill_id: string;
  version: string;
  enabled: boolean;
  priority_override: number | null;
  config_override: Record<string, unknown>;
}

export interface BootstrapTemplate {
  default_version: string;
  skills: BootstrapTemplateSkill[];
}

export interface SyncTemplateResult {
  user_id: number;
  total: number;
  synced_count: number;
  skipped_count: number;
  failed_count: number;
  overwrite_existing: boolean;
}

// ==================== API ====================

export async function getSkills(params?: SkillPageParams): Promise<Skill[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
  if (params?.search) searchParams.set('search', params.search);
  if (params?.has_embedding !== undefined) {
    searchParams.set('has_embedding', String(params.has_embedding));
  }

  const url = `${API_BASE}/skills${searchParams.toString() ? `?${searchParams}` : ''}`;
  const response = await apiFetch(url);
  if (!response.ok) throw new Error('获取技能列表失败');
  return response.json();
}

export async function getAllSkills(params?: SkillListParams & { pageSize?: number }): Promise<Skill[]> {
  const normalizedPageSize = Math.max(
    1,
    Math.min(params?.pageSize ?? DEFAULT_SKILL_PAGE_SIZE, DEFAULT_SKILL_PAGE_SIZE),
  );

  const allSkills: Skill[] = [];
  let skip = 0;

  for (let page = 0; page < MAX_SKILL_FETCH_PAGES; page += 1) {
    const batch = await getSkills({
      skip,
      limit: normalizedPageSize,
      search: params?.search,
      has_embedding: params?.has_embedding,
    });

    allSkills.push(...batch);

    if (batch.length < normalizedPageSize) {
      return allSkills;
    }

    skip += batch.length;
  }

  throw new Error('技能数量过多，分页拉取超过安全上限，请改用分页模式');
}

export async function getSkillDetail(skillId: string): Promise<SkillDetail> {
  const response = await apiFetch(`${API_BASE}/skills/${skillId}`);
  if (!response.ok) throw new Error('获取技能详情失败');
  return response.json();
}

export async function getVectorStatus(): Promise<VectorStatus> {
  const response = await apiFetch(`${API_BASE}/vector-status`);
  if (!response.ok) throw new Error('获取向量状态失败');
  return response.json();
}

export async function regenerateEmbeddings(skillIds?: string[]): Promise<{
  message: string;
  success_count?: number;
  total: number;
  status?: string;
  errors?: string[];
}> {
  const response = await apiFetch(`${API_BASE}/regenerate-embeddings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skill_ids: skillIds || null }),
  });
  if (!response.ok) throw new Error('重新生成向量失败');
  return response.json();
}

export async function regenerateSingleSkill(skillId: string): Promise<{
  message: string;
  skill_id: string;
  embedding_dim: number;
}> {
  const response = await apiFetch(`${API_BASE}/skills/${skillId}/regenerate`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('重新生成向量失败');
  return response.json();
}

export async function deleteSkill(skillId: string): Promise<void> {
  const response = await apiFetch(`${API_BASE}/skills/${skillId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('删除技能失败');
}

export async function searchSkills(
  query: string,
  topK: number = 5,
  threshold: number = 0.3,
): Promise<{
  query: string;
  results: SearchResult[];
  count: number;
}> {
  const params = new URLSearchParams({
    query,
    top_k: String(topK),
    threshold: String(threshold),
  });
  const response = await apiFetch(`${API_BASE}/search?${params}`);
  if (!response.ok) throw new Error('搜索技能失败');
  return response.json();
}

export async function getBootstrapTemplate(): Promise<BootstrapTemplate> {
  const response = await apiFetch(`${API_BASE}/bootstrap-template`);
  if (!response.ok) throw new Error('获取模板失败');
  return response.json();
}

export async function updateBootstrapTemplate(template: BootstrapTemplate): Promise<BootstrapTemplate> {
  const response = await apiFetch(`${API_BASE}/bootstrap-template`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(template),
  });
  if (!response.ok) throw new Error('更新模板失败');
  return response.json();
}

export async function syncUserBootstrapTemplate(
  userId: number,
  overwriteExisting: boolean = false,
): Promise<SyncTemplateResult> {
  const response = await apiFetch(`${API_BASE}/users/${userId}/sync-template`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ overwrite_existing: overwriteExisting }),
  });
  if (!response.ok) throw new Error('模板同步失败');
  return response.json();
}
