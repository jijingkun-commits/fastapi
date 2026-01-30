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

// ==================== API ====================

export async function getSkills(params?: {
  skip?: number;
  limit?: number;
  search?: string;
  has_embedding?: boolean;
}): Promise<Skill[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip !== undefined) searchParams.set('skip', String(params.skip));
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
  if (params?.search) searchParams.set('search', params.search);
  if (params?.has_embedding !== undefined) searchParams.set('has_embedding', String(params.has_embedding));
  
  const url = `${API_BASE}/skills${searchParams.toString() ? '?' + searchParams : ''}`;
  const response = await apiFetch(url);
  if (!response.ok) throw new Error('获取技能列表失败');
  return response.json();
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

export async function searchSkills(query: string, topK: number = 5, threshold: number = 0.3): Promise<{
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
