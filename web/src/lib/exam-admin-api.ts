import { apiFetch, readErrorMessage } from '@/lib/backend';

const API_BASE = '/api/v1/exam-admin';

export interface DatasetOption {
  dataset_id: string;
  label: string;
}

export interface DifficultyDistribution {
  easy: number;
  medium: number;
  hard: number;
}

export interface ScoreStrategy {
  single_choice: number;
  multiple_choice: number;
  judge: number;
  short_answer: number;
}

export interface PaperTemplate {
  paper_title: string;
  single_choice_count: number;
  multiple_choice_count: number;
  judge_count: number;
  short_answer_count: number;
  difficulty_distribution: DifficultyDistribution;
  score_strategy: ScoreStrategy;
  answer_section_enabled: boolean;
  answer_page_break: boolean;
  answer_explanation_mode: 'short';
}

export interface ExamTemplateResponse {
  template: PaperTemplate;
  available_datasets: DatasetOption[];
  limits: { max_total_questions: number; max_active_jobs_per_user: number };
}

export interface ExamJobSummary {
  id: number;
  user_id: number;
  title: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  dataset_ids: string[];
  dataset_labels?: string[];
  asset_id?: number | null;
  minio_object_key?: string | null;
  download_url?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface ExamJobDetail extends ExamJobSummary {
  request_snapshot: Record<string, unknown>;
  result_payload: Record<string, unknown>;
}

export interface CreateExamJobRequest {
  dataset_ids: string[];
  template: PaperTemplate;
}

export async function getExamTemplate(): Promise<ExamTemplateResponse> {
  const response = await apiFetch(`${API_BASE}/template`);
  if (!response.ok) throw new Error(await readErrorMessage(response, '加载出题模板失败'));
  return response.json();
}

export async function createExamJob(payload: CreateExamJobRequest): Promise<ExamJobSummary> {
  const response = await apiFetch(`${API_BASE}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await readErrorMessage(response, '创建出题任务失败'));
  return response.json();
}

export async function listExamJobs(limit = 50): Promise<ExamJobSummary[]> {
  const response = await apiFetch(`${API_BASE}/jobs?limit=${limit}`);
  if (!response.ok) throw new Error(await readErrorMessage(response, '加载历史记录失败'));
  return response.json();
}

export async function getExamJob(jobId: number): Promise<ExamJobDetail> {
  const response = await apiFetch(`${API_BASE}/jobs/${jobId}`);
  if (!response.ok) throw new Error(await readErrorMessage(response, '加载任务详情失败'));
  return response.json();
}

export function getExamDownloadUrl(jobId: number): string {
  return `${API_BASE}/jobs/${jobId}/download`;
}
