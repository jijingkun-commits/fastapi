/**
 * 待办事项 API 客户端（中文注释）
 * 
 * 提供直接调用后端 REST API 的函数,绕过 AI 自然语言处理
 */

import { Todo } from '@/types/todo';
import { apiFetch } from '@/lib/backend';

const API_BASE = '/api/v1/todo';

/**
 * 更新待办事项
 */
export async function updateTodoAPI(
    todoId: number,
    updates: Partial<Todo>
): Promise<void> {
    const response = await apiFetch(`${API_BASE}/${todoId}`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            title: updates.title,
            description: updates.description,
            priority: updates.priority,
            due_date: updates.due_date,
            start_time: updates.start_time,
            category: updates.category,
            status: updates.status,
            progress: updates.progress,
            progress_notes: updates.progress_notes,
        }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: '更新失败' }));
        throw new Error(error.detail || '更新待办失败');
    }
}

/**
 * 完成待办事项
 */
export async function completeTodoAPI(todoId: number): Promise<void> {
    const response = await apiFetch(`${API_BASE}/${todoId}/complete`, {
        method: 'POST',
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: '操作失败' }));
        throw new Error(error.detail || '完成待办失败');
    }
}

/**
 * 删除待办事项
 */
export async function deleteTodoAPI(todoId: number): Promise<void> {
    const response = await apiFetch(`${API_BASE}/${todoId}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: '操作失败' }));
        throw new Error(error.detail || '删除待办失败');
    }
}

/**
 * 刷新待办列表 (通过自然语言)
 */
export async function refreshTodoList(): Promise<Todo[]> {
    const response = await apiFetch(`${API_BASE}`, {
        method: 'GET',
    });

    if (!response.ok) {
        throw new Error('获取待办列表失败');
    }

    return response.json();
}
