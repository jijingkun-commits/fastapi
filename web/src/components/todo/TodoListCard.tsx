/**
 * 待办事项列表卡片 (v2)
 * 
 * 变更记录:
 * - 移除分类 (Category) 和 标签 (Tags) 编辑入口
 * - 新增 开始时间 (Start Time) 编辑
 * - 新增 进展情况 (Progress) 编辑与展示 (进度条 + 备注)
 */
'use client'

import React, { useState, KeyboardEvent } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    CheckCircle,
    Trash2,
    Calendar,
    ChevronDown,
    ChevronUp,
    Edit2,
    Save,
    X,
    Clock,
    Flag,
    Activity
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { updateTodoAPI, completeTodoAPI, deleteTodoAPI } from '@/lib/todo-api'
import { toast } from 'sonner'

// ==================== Types ====================

export interface TodoItem {
    id: number
    title: string
    status: string
    description?: string
    priority: number
    due_date?: string
    start_time?: string
    progress?: number        // 0-100
    progress_notes?: string  // 进展情况/备注
    category?: string        // 保留字段但不展示编辑
    tags?: string[]          // 保留字段但不展示编辑
}

interface TodoListCardProps {
    todos: TodoItem[]
    onAction: (command: string) => void
    readonly?: boolean  // 是否为只读模式(历史记录)
    onSelectionChange?: (todoId: number | null, todo?: TodoItem) => void  // 选中回调
    onRefresh?: () => void  // 刷新回调
}

// ==================== Component ====================

export default function TodoListCard({
    todos = [],
    onAction,
    readonly = false,
    onSelectionChange,
    onRefresh
}: TodoListCardProps) {
    const [selectedItem, setSelectedItem] = useState<number | null>(null)  // 单选
    const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set())
    const [editingId, setEditingId] = useState<number | null>(null)
    const [editForm, setEditForm] = useState<Partial<TodoItem>>({})
    const [isUpdating, setIsUpdating] = useState(false)

    // 单选切换
    const handleSelect = (id: number) => {
        const newSelection = selectedItem === id ? null : id
        setSelectedItem(newSelection)

        const todo = todos.find(t => t.id === id)
        onSelectionChange?.(newSelection, todo)
    }

    // 切换展开
    const toggleExpand = (id: number) => {
        const newExpanded = new Set(expandedItems)
        if (newExpanded.has(id)) {
            newExpanded.delete(id)
        } else {
            newExpanded.add(id)
        }
        setExpandedItems(newExpanded)
    }

    // 开始编辑
    const startEdit = (todo: TodoItem) => {
        setEditingId(todo.id)
        setEditForm({ ...todo })
    }

    // 保存编辑 (直接API调用)
    const handleSave = async () => {
        if (!editingId) return

        const original = todos.find(t => t.id === editingId)
        if (!original) return

        setIsUpdating(true)
        try {
            await updateTodoAPI(editingId, editForm)
            toast.success('更新成功')
            setEditingId(null)
            onRefresh?.()  // 通知父组件刷新
        } catch (error: any) {
            toast.error(error.message || '更新失败')
        } finally {
            setIsUpdating(false)
        }
    }

    // 快速完成 (直接API)
    const handleQuickComplete = async (id: number) => {
        setIsUpdating(true)
        try {
            await completeTodoAPI(id)
            toast.success('已完成')
            onRefresh?.()
        } catch (error: any) {
            toast.error(error.message || '操作失败')
        } finally {
            setIsUpdating(false)
        }
    }

    // 快速重开 (直接API)
    const handleQuickReopen = async (id: number) => {
        setIsUpdating(true)
        try {
            await updateTodoAPI(id, { status: 'todo' })
            toast.success('已重开')
            onRefresh?.()
        } catch (error: any) {
            toast.error(error.message || '操作失败')
        } finally {
            setIsUpdating(false)
        }
    }

    // 快速删除 (直接API)
    const handleQuickDelete = async (id: number) => {
        setIsUpdating(true)
        try {
            await deleteTodoAPI(id)
            toast.success('已删除')
            onRefresh?.()
        } catch (error: any) {
            toast.error(error.message || '操作失败')
        } finally {
            setIsUpdating(false)
        }
    }

    const priorityColors: Record<number, string> = {
        1: 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100',
        2: 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100',
        3: 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100'
    }

    const priorityNames: Record<number, string> = { 1: '高优先级', 2: '中优先级', 3: '低优先级' }

    if (todos.length === 0) {
        return (
            <Card className="bg-gray-50/50 border-dashed shadow-none">
                <CardContent className="p-8 text-center text-gray-500 text-sm flex flex-col items-center gap-2">
                    <CheckCircle className="w-8 h-8 text-gray-300" />
                    没有找到相关待办事项
                </CardContent>
            </Card>
        )
    }

    return (
        <Card className="w-full max-w-2xl border-indigo-100/50 bg-white/90 backdrop-blur-sm shadow-sm overflow-hidden transition-all duration-300 hover:shadow-md">
            <CardContent className="p-0">
                {/* Header */}
                <div className="flex items-center justify-between p-3 border-b border-indigo-50/50 bg-indigo-50/20">
                    <div className="flex items-center gap-3">
                        <span className="font-semibold text-sm text-indigo-950 flex items-center gap-2">
                            <CheckCircle className="w-4 h-4 text-indigo-500" />
                            待办清单 ({todos.length})
                        </span>
                        {selectedItem !== null && (
                            <Badge variant="secondary" className="text-xs bg-indigo-100 text-indigo-700 hover:bg-indigo-100 border-none">
                                已选中 ID {selectedItem}
                            </Badge>
                        )}
                    </div>
                    <div className="flex gap-1.5 transition-all">
                        {!readonly && selectedItem !== null && (
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 text-xs text-gray-500 hover:text-gray-700"
                                onClick={() => handleSelect(selectedItem)}
                            >
                                取消选择
                            </Button>
                        )}
                        {readonly && (
                            <span className="text-xs text-gray-400">历史记录</span>
                        )}
                    </div>
                </div>

                {/* List */}
                <div className="divide-y divide-gray-50">
                    {todos.map((todo) => {
                        const isSelected = selectedItem === todo.id
                        const isExpanded = expandedItems.has(todo.id)
                        const isEditing = editingId === todo.id
                        const isCompleted = todo.status === 'done'

                        return (
                            <div
                                key={todo.id}
                                className={cn(
                                    "transition-all duration-200 group cursor-pointer",
                                    isSelected && "bg-indigo-50/60 border-l-4 border-indigo-500",
                                    !isSelected && "hover:bg-gray-50/50",
                                    isExpanded && "bg-gray-50/30"
                                )}
                                onClick={() => !readonly && !isEditing && handleSelect(todo.id)}
                            >
                                {/* Item Row */}
                                <div className="flex items-start gap-3 p-3.5">

                                    <div className="flex-1 min-w-0 space-y-1.5">
                                        <div className="flex items-start justify-between gap-3">
                                            <div
                                                className="cursor-pointer flex-1 min-w-0"
                                            >
                                                <div className="flex items-center gap-2">
                                                    <span className={cn(
                                                        "font-medium text-sm truncate transition-colors",
                                                        isCompleted ? "text-gray-400 line-through decoration-gray-300" : "text-gray-900 group-hover:text-indigo-900"
                                                    )}>
                                                        {todo.title}
                                                    </span>
                                                    {todo.priority === 1 && !isCompleted && (
                                                        <span className="flex h-1.5 w-1.5 rounded-full bg-red-500 ring-2 ring-red-100" />
                                                    )}
                                                </div>

                                                <div className="flex flex-wrap items-center gap-2 mt-1.5">
                                                    <Badge
                                                        variant="outline"
                                                        className={cn("text-[10px] h-5 px-1.5 font-normal", priorityColors[todo.priority])}
                                                    >
                                                        {priorityNames[todo.priority]}
                                                    </Badge>

                                                    {todo.start_time && (
                                                        <span className="flex items-center gap-1 text-[11px] font-medium px-1.5 py-0.5 rounded-md border bg-indigo-50 text-indigo-600 border-indigo-100">
                                                            <Calendar className="w-3 h-3" />
                                                            {todo.start_time} (开始)
                                                        </span>
                                                    )}

                                                    {todo.due_date && (
                                                        <span className={cn(
                                                            "flex items-center gap-1 text-[11px] font-medium px-1.5 py-0.5 rounded-md border",
                                                            new Date(todo.due_date) < new Date() && !isCompleted
                                                                ? "bg-red-50 text-red-600 border-red-100"
                                                                : "bg-gray-50 text-gray-500 border-gray-200"
                                                        )}>
                                                            <Clock className="w-3 h-3" />
                                                            {todo.due_date} (截止)
                                                        </span>
                                                    )}

                                                    {todo.progress !== undefined && todo.progress > 0 && !isCompleted && (
                                                        <span className="text-[10px] text-emerald-600 font-medium bg-emerald-50 px-1.5 py-0.5 rounded-md border border-emerald-100 flex items-center gap-1">
                                                            <Activity className="w-3 h-3" />
                                                            {todo.progress}%
                                                        </span>
                                                    )}
                                                </div>
                                            </div>

                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-6 w-6 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 -mr-1"
                                                onClick={() => toggleExpand(todo.id)}
                                            >
                                                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                            </Button>
                                        </div>
                                    </div>
                                </div>

                                {/* Expanded Details - Edit Mode */}
                                {isExpanded && isEditing && (
                                    <div className="px-3 pb-3 pt-0 animate-in slide-in-from-top-2 duration-200">
                                        <div className="bg-white p-4 rounded-xl border border-indigo-100 shadow-lg space-y-4 relative overflow-hidden">
                                            {/* Decorative background */}
                                            <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-50 rounded-full blur-3xl -z-10 opacity-50 pointer-events-none" />

                                            {/* 标题 */}
                                            <div className="space-y-1.5">
                                                <label className="text-xs font-medium text-gray-500 flex items-center gap-1.5">标题 <span className="text-red-500">*</span></label>
                                                <Input
                                                    value={editForm.title}
                                                    onChange={e => setEditForm({ ...editForm, title: e.target.value })}
                                                    className="h-9 text-sm font-medium border-gray-200 focus-visible:ring-indigo-500/20 focus-visible:border-indigo-500"
                                                />
                                            </div>

                                            {/* 属性网格 */}
                                            <div className="grid grid-cols-2 gap-4">
                                                {/* 优先级 */}
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-medium text-gray-500 flex items-center gap-1.5">
                                                        <Flag className="w-3 h-3" /> 优先级
                                                    </label>
                                                    <Select
                                                        value={String(editForm.priority)}
                                                        onValueChange={(val) => setEditForm({ ...editForm, priority: Number(val) })}
                                                    >
                                                        <SelectTrigger className="h-9 text-xs border-gray-200 focus:ring-indigo-500/20">
                                                            <SelectValue />
                                                        </SelectTrigger>
                                                        <SelectContent>
                                                            <SelectItem value="1">🔴 高优先级</SelectItem>
                                                            <SelectItem value="2">🟡 中优先级</SelectItem>
                                                            <SelectItem value="3">🔵 低优先级</SelectItem>
                                                        </SelectContent>
                                                    </Select>
                                                </div>

                                                {/* 进度 (%) */}
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-medium text-gray-500 flex items-center gap-1.5">
                                                        <Activity className="w-3 h-3" /> 进度 (%)
                                                    </label>
                                                    <div className="flex items-center gap-2">
                                                        <Input
                                                            type="number"
                                                            min={0}
                                                            max={100}
                                                            value={editForm.progress !== undefined ? editForm.progress : 0}
                                                            onChange={e => setEditForm({ ...editForm, progress: Math.min(100, Math.max(0, parseInt(e.target.value) || 0)) })}
                                                            className="h-9 text-xs border-gray-200 focus:ring-indigo-500/20"
                                                        />
                                                    </div>
                                                </div>

                                                {/* 开始时间 */}
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-medium text-gray-500 flex items-center gap-1.5">
                                                        <Calendar className="w-3 h-3" /> 开始时间
                                                    </label>
                                                    <Input
                                                        value={editForm.start_time || ''}
                                                        onChange={e => setEditForm({ ...editForm, start_time: e.target.value })}
                                                        placeholder="如: 今天下午2点"
                                                        className="h-9 text-sm border-gray-200 focus-visible:ring-indigo-500/20"
                                                    />
                                                </div>

                                                {/* 截止时间 */}
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-medium text-gray-500 flex items-center gap-1.5">
                                                        <Clock className="w-3 h-3" /> 截止时间
                                                    </label>
                                                    <Input
                                                        value={editForm.due_date || ''}
                                                        onChange={e => setEditForm({ ...editForm, due_date: e.target.value })}
                                                        placeholder="如: 明天上午9点"
                                                        className="h-9 text-sm border-gray-200 focus-visible:ring-indigo-500/20"
                                                    />
                                                </div>
                                            </div>

                                            {/* 进展情况 (New) */}
                                            <div className="space-y-1.5">
                                                <label className="text-xs font-medium text-gray-500 flex items-center gap-1.5">
                                                    <Edit2 className="w-3 h-3" /> 进展情况
                                                </label>
                                                <Textarea
                                                    value={editForm.progress_notes || ''}
                                                    onChange={e => setEditForm({ ...editForm, progress_notes: e.target.value })}
                                                    className="min-h-[60px] text-sm resize-none border-gray-200 focus-visible:ring-indigo-500/20"
                                                    placeholder="记录最新进展..."
                                                />
                                            </div>

                                            {/* 详细描述 */}
                                            <div className="space-y-1.5">
                                                <label className="text-xs font-medium text-gray-500">详细描述</label>
                                                <Textarea
                                                    value={editForm.description || ''}
                                                    onChange={e => setEditForm({ ...editForm, description: e.target.value })}
                                                    className="min-h-[80px] text-sm resize-none border-gray-200 focus-visible:ring-indigo-500/20"
                                                    placeholder="添加更多备注信息..."
                                                />
                                            </div>

                                            <div className="flex justify-end gap-3 pt-2 border-t border-gray-50">
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="h-8 text-gray-500 hover:text-gray-700"
                                                    onClick={() => setEditingId(null)}
                                                >
                                                    取消
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    className="h-8 bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm px-4"
                                                    onClick={handleSave}
                                                >
                                                    <Save className="w-3.5 h-3.5 mr-1.5" />
                                                    保存更改
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Expanded Details - View Mode */}
                                {isExpanded && !isEditing && (
                                    <div className="px-3 pb-3 pt-0 animate-in slide-in-from-top-1 duration-200">
                                        <div className="space-y-3 bg-gray-50/50 p-4 rounded-xl border border-gray-100/50">
                                            {/* 进展情况展示 (New Section) */}
                                            {(todo.progress_notes || (todo.progress !== undefined && todo.progress > 0)) && (
                                                <div className="bg-white p-3 rounded-lg border border-indigo-50 space-y-2">
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center gap-1.5 text-xs font-medium text-indigo-900">
                                                            <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                                                            最新进展
                                                        </div>
                                                        {todo.progress !== undefined && (
                                                            <div className="text-[10px] text-gray-400">
                                                                进度: {todo.progress}%
                                                            </div>
                                                        )}
                                                    </div>

                                                    {/* 进度条 */}
                                                    {todo.progress !== undefined && todo.progress > 0 && (
                                                        <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                                                            <div
                                                                className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                                                                style={{ width: `${todo.progress}%` }}
                                                            />
                                                        </div>
                                                    )}

                                                    {todo.progress_notes && (
                                                        <p className="text-xs text-secondary-foreground leading-relaxed whitespace-pre-wrap pl-3 border-l-2 border-indigo-200 mt-1">
                                                            {todo.progress_notes}
                                                        </p>
                                                    )}
                                                </div>
                                            )}

                                            {todo.description && (
                                                <div className="space-y-1">
                                                    <div className="text-xs font-medium text-gray-500">描述</div>
                                                    <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">
                                                        {todo.description}
                                                    </p>
                                                </div>
                                            )}

                                            <div className="flex items-center justify-between pt-3 border-t border-gray-200/50 mt-2">
                                                <div className="text-xs text-gray-400 flex flex-col gap-0.5">
                                                    <span>ID: #{todo.id}</span>
                                                    {todo.category && <span>分类: {todo.category}</span>}
                                                </div>
                                                <div className="flex gap-2">
                                                    {!readonly && (
                                                        <Button
                                                            size="sm"
                                                            variant="outline"
                                                            className="h-7 text-xs bg-white border-gray-200 hover:bg-indigo-50 hover:text-indigo-600 hover:border-indigo-200 transition-all font-normal"
                                                            onClick={(e) => {
                                                                e.stopPropagation()
                                                                startEdit(todo)
                                                            }}
                                                        >
                                                            <Edit2 className="w-3 h-3 mr-1.5" />
                                                            编辑
                                                        </Button>
                                                    )}
                                                    {!readonly && (
                                                        <Button
                                                            size="sm"
                                                            variant="ghost"
                                                            className={cn(
                                                                "h-7 text-xs transition-all font-medium border shadow-sm",
                                                                isCompleted
                                                                    ? "bg-white border-gray-200 text-gray-500 hover:bg-gray-50"
                                                                    : "bg-emerald-50 border-emerald-100 text-emerald-600 hover:bg-emerald-100 hover:text-emerald-700 hover:border-emerald-200"
                                                            )}
                                                            onClick={(e) => {
                                                                e.stopPropagation()
                                                                if (isCompleted) {
                                                                    handleQuickReopen(todo.id);
                                                                } else {
                                                                    handleQuickComplete(todo.id);
                                                                }
                                                            }}
                                                        >
                                                            <CheckCircle className="w-3 h-3 mr-1.5" />
                                                            {isCompleted ? '重新打开' : '标记完成'}
                                                        </Button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>
            </CardContent>
        </Card>
    )
}
