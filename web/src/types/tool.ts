/**
 * 工具执行状态与 UI 组件类型定义
 * 
 * 借鉴自 assistant-ui 的 ToolCallMessagePartStatus
 * @see https://www.assistant-ui.com/docs/guides/ToolUI
 */

// ==================== 工具状态类型 ====================

/**
 * 工具执行状态
 * 
 * 状态说明：
 * - running: 工具正在执行中
 * - requires-action: 需要用户确认/输入
 * - complete: 执行完成
 * - incomplete: 执行未完成（取消/错误/未知原因）
 */
export type ToolStatus<TArgs = unknown, TResult = unknown> =
    | { type: 'running' }
    | { type: 'requires-action'; action: string; args: TArgs }
    | { type: 'complete'; result: TResult }
    | { type: 'incomplete'; reason: 'cancelled' | 'error' | 'unknown'; error?: string }


// ==================== 工具 UI Props ====================

/**
 * 工具 UI 组件通用 Props
 * 
 * 借鉴 assistant-ui 的 ToolCallMessagePartProps
 */
export interface ToolUIProps<TArgs = Record<string, unknown>, TResult = unknown> {
    // 工具参数
    args: TArgs
    argsText?: string
    
    // 执行状态
    status: ToolStatus<TArgs, TResult>
    
    // 工具结果
    result?: TResult
    isError?: boolean
    
    // 工具元数据
    toolName: string
    toolCallId?: string
    
    // 交互回调
    onConfirm: (data?: Partial<TArgs>) => void
    onCancel: () => void
    onRetry?: () => void
    
    // Human-in-the-loop 支持
    addResult?: (result: TResult) => void
}

/**
 * 工具 UI 组件类型
 */
export type ToolUIComponent<TArgs = Record<string, unknown>, TResult = unknown> = 
    React.ComponentType<ToolUIProps<TArgs, TResult>>


// ==================== 确认卡片专用类型 ====================

/**
 * 确认数据结构（与后端 pending_operation 对应）
 */
export interface ConfirmationData {
    action: TodoAction
    data: Record<string, unknown>
    summary?: string
    target_task?: { id: number; title: string }
    diff?: Record<string, { old: unknown; new: unknown }>
}

/**
 * 待办操作类型
 * 注：batch_create/batch_complete 已废弃（2026-02-01），系统不支持批量意图
 */
export type TodoAction = 
    | 'create' 
    | 'update' 
    | 'delete' 
    | 'complete' 
    | 'merge'
    | string // 兜底

/**
 * 确认卡片 Props
 */
export interface ConfirmationCardProps {
    operation: ConfirmationData
    onConfirm: (data?: Record<string, unknown>) => void
    onCancel: () => void
}

/**
 * 子卡片组件 Props（用于拆分后的各类卡片）
 */
export interface SubCardProps {
    data: Record<string, unknown>
    targetTask?: { id: number; title: string }
    diff?: Record<string, { old: unknown; new: unknown }>
    summary?: string
    onConfirm: (data?: Record<string, unknown>) => void
    onCancel: () => void
}


// ==================== 辅助类型 ====================

/**
 * 待办项数据结构（用于卡片展示）
 */
export interface TodoItemData {
    title: string
    time?: string
    due_date?: string
    priority?: number | string
    category?: string
    description?: string
    location?: string
    tags?: string[]
}

/**
 * 字段翻译映射
 */
export const FIELD_TRANSLATIONS: Record<string, string> = {
    title: '标题',
    description: '描述',
    due_date: '截止时间',
    time: '时间',
    priority: '优先级',
    category: '分类',
    progress: '进度',
    location: '地点',
    tags: '标签',
    status: '状态',
}

/**
 * 翻译字段名
 */
export function translateField(field: string): string {
    return FIELD_TRANSLATIONS[field] || field
}

/**
 * 优先级到中文映射
 */
export const PRIORITY_LABELS: Record<number | string, string> = {
    1: '🔴 高',
    2: '🟡 中',
    3: '🟢 低',
    '高': '🔴 高',
    '中': '🟡 中',
    '低': '🟢 低',
}

/**
 * 获取优先级标签
 */
export function getPriorityLabel(priority?: number | string): string {
    if (priority === undefined || priority === null) return '🟡 中'
    return PRIORITY_LABELS[priority] || '🟡 中'
}
