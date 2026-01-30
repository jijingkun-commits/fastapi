/**
 * 数据访问控制管理 API 客户端（中文注释）
 * 
 * 提供：
 * - 表白名单管理
 * - 表黑名单管理  
 * - Schema 白名单管理
 * - SQL 权限测试
 */

import { apiFetch } from '@/lib/backend';

const API_BASE = '/api/v1/access-admin';

// ==================== 类型定义 ====================

export interface AccessConfig {
  whitelist: string[];
  whitelist_source: string;
  blacklist: string[];
  schema_whitelist: string[];
}

export interface TableWhitelist {
  tables: string[];
  source: string;
}

export interface TableBlacklist {
  tables: string[];
}

export interface SchemaWhitelist {
  schemas: string[];
}

export interface SQLTestResult {
  is_valid: boolean;
  error: string | null;
  tables_found: string[];
  tables_allowed: string[];
  tables_denied: string[];
}

export interface AvailableTable {
  schema: string;
  table: string;
  full_name: string;
}

// ==================== 配置获取 ====================

/**
 * 获取完整的访问控制配置
 */
export async function getAccessConfig(): Promise<AccessConfig> {
  const response = await apiFetch(`${API_BASE}/config`);
  if (!response.ok) {
    throw new Error('获取访问控制配置失败');
  }
  return response.json();
}

// ==================== 表白名单 ====================

/**
 * 获取表白名单
 */
export async function getTableWhitelist(): Promise<TableWhitelist> {
  const response = await apiFetch(`${API_BASE}/whitelist`);
  if (!response.ok) {
    throw new Error('获取表白名单失败');
  }
  return response.json();
}

/**
 * 更新表白名单
 */
export async function updateTableWhitelist(tables: string[]): Promise<{ message: string; tables: string[]; count: number }> {
  const response = await apiFetch(`${API_BASE}/whitelist`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tables }),
  });
  if (!response.ok) {
    throw new Error('更新表白名单失败');
  }
  return response.json();
}

/**
 * 添加表到白名单
 */
export async function addToWhitelist(tableName: string): Promise<{ message: string; tables: string[] }> {
  const response = await apiFetch(`${API_BASE}/whitelist/add?table_name=${encodeURIComponent(tableName)}`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('添加表到白名单失败');
  }
  return response.json();
}

/**
 * 从白名单移除表
 */
export async function removeFromWhitelist(tableName: string): Promise<{ message: string; tables: string[] }> {
  const response = await apiFetch(`${API_BASE}/whitelist/${encodeURIComponent(tableName)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('从白名单移除表失败');
  }
  return response.json();
}

// ==================== 表黑名单 ====================

/**
 * 获取表黑名单
 */
export async function getTableBlacklist(): Promise<TableBlacklist> {
  const response = await apiFetch(`${API_BASE}/blacklist`);
  if (!response.ok) {
    throw new Error('获取表黑名单失败');
  }
  return response.json();
}

/**
 * 更新表黑名单
 */
export async function updateTableBlacklist(tables: string[]): Promise<{ message: string; tables: string[]; count: number }> {
  const response = await apiFetch(`${API_BASE}/blacklist`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tables }),
  });
  if (!response.ok) {
    throw new Error('更新表黑名单失败');
  }
  return response.json();
}

// ==================== Schema 白名单 ====================

/**
 * 获取 Schema 白名单
 */
export async function getSchemaWhitelist(): Promise<SchemaWhitelist> {
  const response = await apiFetch(`${API_BASE}/schema-whitelist`);
  if (!response.ok) {
    throw new Error('获取 Schema 白名单失败');
  }
  return response.json();
}

/**
 * 更新 Schema 白名单
 */
export async function updateSchemaWhitelist(schemas: string[]): Promise<{ message: string; schemas: string[]; count: number }> {
  const response = await apiFetch(`${API_BASE}/schema-whitelist`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ schemas }),
  });
  if (!response.ok) {
    throw new Error('更新 Schema 白名单失败');
  }
  return response.json();
}

// ==================== SQL 测试 ====================

/**
 * 测试 SQL 权限
 */
export async function testSQLAccess(sql: string): Promise<SQLTestResult> {
  const response = await apiFetch(`${API_BASE}/test-sql`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sql }),
  });
  if (!response.ok) {
    throw new Error('SQL 权限测试失败');
  }
  return response.json();
}

// ==================== 可用表 ====================

/**
 * 获取业务数据库中所有可用的表
 */
export async function getAvailableTables(): Promise<{ tables: AvailableTable[]; count: number }> {
  const response = await apiFetch(`${API_BASE}/available-tables`);
  if (!response.ok) {
    throw new Error('获取可用表列表失败');
  }
  return response.json();
}
