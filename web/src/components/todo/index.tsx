/**
 * TodoListCard - 待办列表卡片组件
 * 
 * 重构版本：
 * - 拆分为子组件（TodoItem/TodoItemEdit/TodoItemView）
 * - 使用 useTodoListState hook 统一状态管理
 * - 支持双击编辑、Popover 删除确认、键盘快捷键
 * - 支持筛选和搜索
 * - 支持本地乐观更新（删除/完成/更新后直接更新本地状态）
 */
"use client"

import React, { useCallback, useEffect, useState, useMemo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { CheckCircle, Search, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Todo } from '@/types/todo'
import { updateTodoAPI, completeTodoAPI, deleteTodoAPI, refreshTodoList } from '@/lib/todo-api'
import { toast } from 'sonner'

import { useTodoListState } from './useTodoListState'
import TodoItem from './TodoItem'

// ==================== Types ====================

interface TodoListCardProps {
    todos: Todo[]
    onAction?: (command: string) => void
    readonly?: boolean
    fetchLatest?: boolean
    onSelectionChange?: (todoId: number | null, todo?: Todo) => void
    onRefresh?: () => void
}

// ==================== Component ====================

export default function TodoListCard({
    todos,
    onAction,
    readonly = false,
    fetchLatest = false,
    onSelectionChange,
    onRefresh
}: TodoListCardProps) {
    // 本地待办列表状态（乐观更新）
    const [localTodos, setLocalTodos] = useState<Todo[]>(todos)
    
    // 当 props.todos 变化时同步到本地状态
    useEffect(() => {
        setLocalTodos(todos)
    }, [todos])

    // 如果是最新消息，从 API 获取实时数据
    useEffect(() => {
        if (fetchLatest) {
            refreshTodoList()
                .then(latestTodos => {
                    setLocalTodos(latestTodos)
                })
                .catch(err => {
                    console.warn('获取最新待办列表失败，使用快照数据:', err)
                })
        }
    }, [fetchLatest])

    // 筛选状态
    const [searchQuery, setSearchQuery] = useState('')
    const [statusFilter, setStatusFilter] = useState<'all' | 'todo' | 'done'>('all')
    const [priorityFilter, setPriorityFilter] = useState<'all' | '1' | '2' | '3'>('all')

    // 筛选后的待办列表（使用本地状态）
    const filteredTodos = useMemo(() => {
        return localTodos.filter(todo => {
            // 搜索过滤
            if (searchQuery) {
                const query = searchQuery.toLowerCase()
                const matchTitle = todo.title.toLowerCase().includes(query)
                const matchDesc = todo.description?.toLowerCase().includes(query)
                const matchCategory = todo.category?.toLowerCase().includes(query)
                if (!matchTitle && !matchDesc && !matchCategory) return false
            }
            // 状态过滤
            if (statusFilter !== 'all') {
                if (statusFilter === 'todo' && todo.status === 'done') return false
                if (statusFilter === 'done' && todo.status !== 'done') return false
            }
            // 优先级过滤
            if (priorityFilter !== 'all') {
                if (String(todo.priority) !== priorityFilter) return false
            }
            return true
        })
    }, [localTodos, searchQuery, statusFilter, priorityFilter])

    const hasActiveFilters = searchQuery || statusFilter !== 'all' || priorityFilter !== 'all'

    const clearFilters = () => {
        setSearchQuery('')
        setStatusFilter('all')
        setPriorityFilter('all')
    }

    const {
        state,
        handleSelect,
        toggleExpand,
        startEdit,
        updateEditForm,
        cancelEdit,
        setUpdating
    } = useTodoListState(filteredTodos, { onSelectionChange })

    const { selectedId, expandedIds, editingId, editForm, isUpdating } = state

    // 保存编辑 (Diff 更新 + 本地乐观更新)
    const handleSave = useCallback(async () => {
        if (!editingId) return

        const original = localTodos.find(t => t.id === editingId)
        if (!original) return

        // 计算差异
        const changes: Partial<Todo> = {}
        let hasChanges = false

        const fieldsToCheck: (keyof Todo)[] = [
            'title', 'description', 'priority', 'due_date',
            'start_time', 'progress', 'progress_notes', 'category'
        ]

        fieldsToCheck.forEach(key => {
            if (editForm[key] !== original[key]) {
                (changes as Record<string, unknown>)[key] = editForm[key]
                hasChanges = true
            }
        })

        if (!hasChanges) {
            toast.info('没有检测到修改')
            cancelEdit()
            return
        }

        setUpdating(true)
        try {
            await updateTodoAPI(editingId, changes)
            // 本地乐观更新：直接更新本地状态
            setLocalTodos(prev => prev.map(t => 
                t.id === editingId ? { ...t, ...changes } : t
            ))
            toast.success('更新成功')
            cancelEdit()
        } catch (error: unknown) {
            const message = error instanceof Error ? error.message : '更新失败'
            toast.error(message)
        } finally {
            setUpdating(false)
        }
    }, [editingId, editForm, localTodos, cancelEdit, setUpdating])

    // 快速完成（本地乐观更新）
    const handleQuickComplete = useCallback(async (id: number) => {
        setUpdating(true)
        try {
            await completeTodoAPI(id)
            // 本地乐观更新：标记为已完成
            setLocalTodos(prev => prev.map(t => 
                t.id === id ? { ...t, status: 'done' as const } : t
            ))
            toast.success('已完成')
        } catch (error: unknown) {
            const message = error instanceof Error ? error.message : '操作失败'
            toast.error(message)
        } finally {
            setUpdating(false)
        }
    }, [setUpdating])

    // 删除（本地乐观更新）
    const handleDelete = useCallback(async (id: number) => {
        setUpdating(true)
        try {
            await deleteTodoAPI(id)
            // 本地乐观更新：从列表中移除
            setLocalTodos(prev => prev.filter(t => t.id !== id))
            toast.success('已删除')
        } catch (error: unknown) {
            const message = error instanceof Error ? error.message : '删除失败'
            toast.error(message)
        } finally {
            setUpdating(false)
        }
    }, [setUpdating])

    // 双击进入编辑
    const handleDoubleClick = useCallback((todo: Todo) => {
        if (!readonly) {
            startEdit(todo)
        }
    }, [readonly, startEdit])

    // 键盘快捷键
    useEffect(() => {
        if (readonly) return

        const handleKeyDown = (e: KeyboardEvent) => {
            // 如果在输入框中，不处理快捷键
            if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
                return
            }

            const selectedTodo = localTodos.find(t => t.id === selectedId)
            if (!selectedTodo) return

            switch (e.key) {
                case 'e':
                case 'E':
                    e.preventDefault()
                    startEdit(selectedTodo)
                    break
                case 'Enter':
                    if (!editingId) {
                        e.preventDefault()
                        handleQuickComplete(selectedTodo.id)
                    }
                    break
                case 'Escape':
                    if (editingId) {
                        e.preventDefault()
                        cancelEdit()
                    }
                    break
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [readonly, selectedId, editingId, localTodos, startEdit, cancelEdit, handleQuickComplete])

    // 空状态
    if (localTodos.length === 0) {
        return (
            <Card className="bg-muted/10 border-dashed shadow-none">
                <CardContent className="p-8 text-center text-muted-foreground text-sm flex flex-col items-center gap-2">
                    <CheckCircle className="w-8 h-8 text-muted-foreground/30" />
                    没有找到相关待办事项
                </CardContent>
            </Card>
        )
    }

    return (
        <Card className="w-full max-w-2xl bg-card shadow-sm overflow-hidden transition-all duration-300 hover:shadow-md py-0 gap-0">
            <CardContent className="p-0">
                {/* Header */}
                <div className="flex items-center justify-between p-3 border-b bg-muted/20">
                    <div className="flex items-center gap-3">
                        <span className="font-semibold text-sm flex items-center gap-2">
                            <CheckCircle className="w-4 h-4 text-primary" />
                            待办清单 ({filteredTodos.length}/{localTodos.length})
                        </span>
                        {selectedId !== null && (
                            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                                按 E 编辑 | Enter 完成
                            </span>
                        )}
                    </div>
                    {readonly && (
                        <span className="text-xs text-muted-foreground">历史记录</span>
                    )}
                </div>

                {/* 筛选栏 */}
                {localTodos.length > 3 && (
                    <div className="flex items-center gap-2 p-2 border-b bg-muted/10 flex-wrap">
                        {/* 搜索框 */}
                        <div className="relative flex-1 min-w-[120px] max-w-[200px]">
                            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                            <Input
                                placeholder="搜索..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="h-7 text-xs pl-7 pr-2"
                            />
                        </div>

                        {/* 状态筛选 */}
                        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as typeof statusFilter)}>
                            <SelectTrigger className="h-7 w-[80px] text-xs">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">全部</SelectItem>
                                <SelectItem value="todo">待完成</SelectItem>
                                <SelectItem value="done">已完成</SelectItem>
                            </SelectContent>
                        </Select>

                        {/* 优先级筛选 */}
                        <Select value={priorityFilter} onValueChange={(v) => setPriorityFilter(v as typeof priorityFilter)}>
                            <SelectTrigger className="h-7 w-[80px] text-xs">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">优先级</SelectItem>
                                <SelectItem value="1">高</SelectItem>
                                <SelectItem value="2">中</SelectItem>
                                <SelectItem value="3">低</SelectItem>
                            </SelectContent>
                        </Select>

                        {/* 清除筛选 */}
                        {hasActiveFilters && (
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 px-2 text-xs text-muted-foreground"
                                onClick={clearFilters}
                            >
                                <X className="w-3 h-3 mr-1" />
                                清除
                            </Button>
                        )}
                    </div>
                )}

                {/* List */}
                <div className="divide-y">
                    {filteredTodos.length === 0 && hasActiveFilters ? (
                        <div className="p-6 text-center text-muted-foreground text-sm">
                            <p>没有匹配的待办事项</p>
                            <Button
                                variant="link"
                                size="sm"
                                className="mt-2 text-primary"
                                onClick={clearFilters}
                            >
                                清除筛选条件
                            </Button>
                        </div>
                    ) : (
                        filteredTodos.map((todo, index) => (
                            <TodoItem
                                key={`${todo.id}-${index}`}
                                todo={todo}
                                isSelected={selectedId === todo.id}
                                isExpanded={expandedIds.has(todo.id)}
                                isEditing={editingId === todo.id}
                                editForm={editForm}
                                isUpdating={isUpdating}
                                readonly={readonly}
                                onSelect={handleSelect}
                                onDoubleClick={handleDoubleClick}
                                onToggleExpand={toggleExpand}
                                onStartEdit={startEdit}
                                onUpdateForm={updateEditForm}
                                onSave={handleSave}
                                onCancelEdit={cancelEdit}
                                onComplete={handleQuickComplete}
                                onDelete={handleDelete}
                            />
                        ))
                    )}
                </div>
            </CardContent>
        </Card>
    )
}

// 兼容旧的导入方式
export { default as TodoListCard } from './index'
