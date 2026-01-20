/**
 * 待办任务类型定义（中文注释）
 */

// 基础类型
export type TodoStatus =
    | 'todo'
    | 'in_progress'
    | 'done'
    | 'on_hold'
    | 'cancelled'

export type TodoPriority = 1 | 2 | 3

export type RecurrencePattern =
    | 'daily'
    | 'weekly'
    | 'monthly'
    | 'custom'

// 待办任务接口
export interface Todo {
    id: number
    title: string
    description?: string
    status: TodoStatus
    priority: TodoPriority
    progress: number
    progress_notes?: string  // 进展备注
    category?: string
    tags?: string[]
    due_date?: string
    start_time?: string
    actual_completion_time?: string
    create_time?: string
    is_completed: boolean

    // 重复任务
    is_recurring?: boolean
    recurrence_pattern?: RecurrencePattern
    recurrence_interval?: number
    recurrence_days?: number[]
    recurrence_end_date?: string
    parent_recurring_id?: number

    // 子任务
    parent_id?: number
    task_order?: number
    depth_level?: number
}

export interface RecurringConfigRequest {
    pattern: RecurrencePattern
    interval?: number
    days?: number[]
    end_date?: string
}

// API响应类型
export interface ApiResponse<T> {
    success: boolean
    data?: T
    message?: string
    error?: string
}
