/**
 * 结果增强规则类型定义（中文注释）
 */

export interface ResultEnrichmentRule {
  id: number;
  rule_code: string;
  rule_name: string;
  enabled: boolean;
  priority: number;
  key_column_candidates: string[];
  target_column: string;
  source_table: string;
  source_key_column: string;
  source_value_column: string;
  source_date_column: string | null;
  result_date_column_candidates: string[];
  description: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ResultEnrichmentRulePayload {
  rule_code: string;
  rule_name: string;
  enabled: boolean;
  priority: number;
  key_column_candidates: string[];
  target_column: string;
  source_table: string;
  source_key_column: string;
  source_value_column: string;
  source_date_column?: string | null;
  result_date_column_candidates: string[];
  description?: string | null;
}

export interface ResultEnrichmentRuleTestRequest {
  rows: Record<string, unknown>[];
  columns: string[];
  rule_id?: number;
}

export interface ResultEnrichmentRuleTestResponse {
  rows: Record<string, unknown>[];
  columns: string[];
  applied_rule_codes: string[];
}

export interface ResultEnrichmentRuleRefreshResponse {
  message: string;
  rule_count: number;
  ttl_seconds: number;
}
