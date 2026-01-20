"use client"

import React, { useState } from 'react'
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
    Clock,
    Flag,
    Activity,
    Loader2,
    Repeat,
    Tag
} from 'lucide-react'
import { format, isToday, isTomorrow, isThisYear } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { cn } from '@/lib/utils'
import { updateTodoAPI, completeTodoAPI, deleteTodoAPI } from '@/lib/todo-api'
import { toast } from 'sonner'
import { Progress } from "@/components/ui/progress"

import { Todo } from '@/types/todo'

// ==================== Types ====================
// 使用统一类型，不再重复定义 TodoItem

interface TodoListCardProps {
    todos: Todo[]
    onAction?: (command: string) => void  // 恢复可选属性
    readonly?: boolean
    onSelectionChange?: (todoId: number | null, todo?: Todo) => void  // 恢复可选属性
    onRefresh?: () => void
}

// ==================== Component ====================

export default function TodoListCard({
    todos,
    onAction,
    readonly = false,
    onSelectionChange,
    onRefresh
}: TodoListCardProps) {
    const [selectedItem, setSelectedItem] = useState<number | null>(null)  // 单选
    const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set())
    const [editingId, setEditingId] = useState<number | null>(null)
    const [editForm, setEditForm] = useState<Partial<Todo>>({})
    const [isUpdating, setIsUpdating] = useState(false)

    // 日期格式化辅助函数
    const formatFriendlyDate = (dateStr?: string) => {
        if (!dateStr) return ''
        try {
            const date = new Date(dateStr)
            if (isToday(date)) {
                return format(date, "'今天' HH:mm", { locale: zhCN })
            }
            if (isTomorrow(date)) {
                return format(date, "'明天' HH:mm", { locale: zhCN })
            }
            if (isThisYear(date)) {
                return format(date, "MM月dd日 HH:mm", { locale: zhCN })
            }
            return format(date, "yyyy-MM-dd HH:mm", { locale: zhCN })
        } catch (e) {
            return dateStr
        }
    }

    // datetime-local 格式转换 (YYYY-MM-DDThh:mm)
    const toDatetimeLocal = (isoStr?: string) => {
        if (!isoStr) return ''
        try {
            // 如果只有日期没有时间 (YYYY-MM-DD)，补上时间
            if (isoStr.length === 10) return `${isoStr}T09:00`
            return new Date(isoStr).toISOString().slice(0, 16)
        } catch (e) {
            return ''
        }
    }

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

    // 开始编辑（同时展开）
    const startEdit = (todo: Todo) => {
        setEditingId(todo.id)
        setEditForm({ ...todo })
        // 自动展开该项
        setExpandedItems(prev => new Set(prev).add(todo.id))
    }

    // 保存编辑 (Diff 更新)
    const handleSave = async () => {
        if (!editingId) return

        const original = todos.find(t => t.id === editingId)
        if (!original) return

        // 计算差异
        const changes: Partial<Todo> = {}
        let hasChanges = false

        // 比较关键字段
        const fieldsToCheck: (keyof Todo)[] = [
            'title', 'description', 'priority', 'due_date',
            'start_time', 'progress', 'progress_notes', 'category'
        ]

        fieldsToCheck.forEach(key => {
            if (editForm[key] !== original[key]) {
                // @ts-ignore - 动态赋值类型检查较松
                changes[key] = editForm[key]
                hasChanges = true
            }
        })

        if (!hasChanges) {
            toast.info('没有检测到修改')
            setEditingId(null)
            return
        }

        setIsUpdating(true)
        try {
            await updateTodoAPI(editingId, changes)
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
                {/* Header - 简洁版 */}
                <div className="flex items-center justify-between p-3 border-b bg-muted/20">
                    <div className="flex items-center gap-3">
                        <span className="font-semibold text-sm flex items-center gap-2">
                            <CheckCircle className="w-4 h-4 text-primary" />
                            待办清单 ({todos.length})
                        </span>
                        {selectedItem !== null && (
                            <Badge variant="secondary" className="text-xs bg-primary/10 text-primary hover:bg-primary/20 border-none font-normal">
                                已选中 ID {selectedItem}
                            </Badge>
                        )}
                    </div>
                    {readonly && (
                        <span className="text-xs text-muted-foreground">历史记录</span>
                    )}
                </div>

                {/* List - 紧凑化布局 */}
                <div className="divide-y">
                    {todos.map((todo, index) => {
                        const isSelected = selectedItem === todo.id
                        const isExpanded = expandedItems.has(todo.id)
                        const isEditing = editingId === todo.id
                        const isCompleted = todo.status === 'done'

                        return (
                            <div
                                key={`${todo.id}-${index}`}
                                className={cn(
                                    "transition-all duration-200 group cursor-pointer border-l-4 border-transparent",
                                    isSelected && "bg-muted/30 border-primary",
                                    !isSelected && "hover:bg-muted/30",
                                    isExpanded && "bg-muted/20"
                                )}
                                onClick={() => !readonly && !isEditing && handleSelect(todo.id)}
                            >
                                {/* Item Row - 紧凑布局 */}
                                <div className="flex items-center gap-3 p-3">
                                    <div className="flex-1 min-w-0">
                                        {/* 第一行：标题 + 优先级 + 截止时间 + 右侧按钮 */}
                                        <div className="flex items-center justify-between gap-2">
                                            <div className="flex items-center gap-2 flex-1 min-w-0">
                                                {/* 标题（限制字符） */}
                                                <span className={cn(
                                                    "font-medium text-sm transition-colors flex-shrink-0",
                                                    isCompleted ? "text-muted-foreground line-through decoration-border" : "text-foreground"
                                                )}>
                                                    {todo.title.length > 10 ? `${todo.title.slice(0, 10)}...` : todo.title}
                                                </span>

                                                {/* 重复任务图标 */}
                                                {todo.is_recurring && (
                                                    <span
                                                        className="flex items-center text-blue-500"
                                                        title={`${todo.recurrence_pattern === 'daily' ? '每日' : todo.recurrence_pattern === 'weekly' ? '每周' : '每月'}重复`}
                                                    >
                                                        <Repeat className="w-3 h-3" />
                                                    </span>
                                                )}

                                                {/* 优先级标签 */}
                                                <span className={cn("px-1.5 py-0.5 rounded text-[10px] font-medium border flex-shrink-0", priorityColors[todo.priority])}>
                                                    {priorityNames[todo.priority]}
                                                </span>

                                                {/* 截止时间 */}
                                                {todo.due_date && (
                                                    <span className={cn(
                                                        "flex items-center gap-1 text-xs flex-shrink-0",
                                                        new Date(todo.due_date) < new Date() && !isCompleted ? "text-destructive font-medium" : "text-muted-foreground"
                                                    )}>
                                                        <Clock className="w-3 h-3" />
                                                        {formatFriendlyDate(todo.due_date)}
                                                    </span>
                                                )}
                                            </div>

                                            {/* 右侧按钮区 */}
                                            <div className="flex items-center gap-1 flex-shrink-0">
                                                {/* 选中时显示编辑和完成按钮 */}
                                                {!readonly && isSelected && (
                                                    <>
                                                        <Button
                                                            size="sm"
                                                            variant="outline"
                                                            className="h-6 text-xs font-normal px-2"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                startEdit(todo);
                                                            }}
                                                        >
                                                            <Edit2 className="w-3 h-3 mr-1" />
                                                            编辑
                                                        </Button>
                                                        <Button
                                                            size="sm"
                                                            variant="ghost"
                                                            className={cn(
                                                                "h-6 text-xs font-medium px-2 border",
                                                                isCompleted
                                                                    ? "text-muted-foreground hover:bg-muted"
                                                                    : "bg-emerald-50 dark:bg-emerald-950/20 border-emerald-100 dark:border-emerald-900 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100"
                                                            )}
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                if (isCompleted) {
                                                                    handleQuickReopen(todo.id);
                                                                } else {
                                                                    handleQuickComplete(todo.id);
                                                                }
                                                            }}
                                                        >
                                                            <CheckCircle className="w-3 h-3 mr-1" />
                                                            {isCompleted ? '重开' : '完成'}
                                                        </Button>
                                                    </>
                                                )}
                                                {/* 展开按钮 */}
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-6 w-6 text-muted-foreground hover:text-primary hover:bg-primary/10"
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        toggleExpand(todo.id)
                                                    }}
                                                >
                                                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                                </Button>
                                            </div>
                                        </div>

                                        {/* 第二行：进度条 + 分类标签 + 描述 */}
                                        <div className="mt-1 space-y-1">
                                            {/* 进度条（仅在有进度且未完成时显示） */}
                                            {todo.progress > 0 && todo.progress < 100 && (
                                                <div className="flex items-center gap-2">
                                                    <Progress value={todo.progress} className="h-1.5 flex-1" />
                                                    <span className="text-[10px] text-muted-foreground w-8">{todo.progress}%</span>
                                                </div>
                                            )}

                                            {/* 分类和标签 */}
                                            {(todo.category || (todo.tags && todo.tags.length > 0)) && (
                                                <div className="flex items-center gap-1.5 flex-wrap">
                                                    {todo.category && (
                                                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] bg-muted text-muted-foreground">
                                                            <Tag className="w-2.5 h-2.5" />
                                                            {todo.category}
                                                        </span>
                                                    )}
                                                    {todo.tags?.slice(0, 2).map((tag, i) => (
                                                        <span key={i} className="px-1.5 py-0.5 rounded text-[10px] bg-primary/10 text-primary">
                                                            {tag}
                                                        </span>
                                                    ))}
                                                    {todo.tags && todo.tags.length > 2 && (
                                                        <span className="text-[10px] text-muted-foreground">+{todo.tags.length - 2}</span>
                                                    )}
                                                </div>
                                            )}

                                            {/* 描述（仅在有内容时显示） */}
                                            {todo.description && (
                                                <p className="text-xs text-muted-foreground truncate">
                                                    {todo.description}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Expanded Details - Edit Mode */}
                                {isExpanded && isEditing && (
                                    <div className="px-3 pb-3 pt-0 animate-in slide-in-from-top-2 duration-200">
                                        <div className="bg-card p-4 rounded-xl border shadow-sm space-y-4">

                                            {/* 标题 */}
                                            <div className="space-y-1.5">
                                                <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">标题 <span className="text-destructive">*</span></label>
                                                <Input
                                                    value={editForm.title}
                                                    onChange={e => setEditForm({ ...editForm, title: e.target.value })}
                                                    className="h-9 text-sm font-medium"
                                                />
                                            </div>

                                            {/* 属性网格 */}
                                            <div className="grid grid-cols-2 gap-4">
                                                {/* 优先级 */}
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                                                        <Flag className="w-3 h-3" /> 优先级
                                                    </label>
                                                    <Select
                                                        value={String(editForm.priority)}
                                                        onValueChange={(val) => setEditForm({ ...editForm, priority: Number(val) as any })}  // 使用 any 规避类型检查，或者导入 TodoPriority 做断言
                                                    >
                                                        <SelectTrigger className="h-9 text-xs">
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
                                                    <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                                                        <Activity className="w-3 h-3" /> 进度 (%)
                                                    </label>
                                                    <div className="flex items-center gap-2">
                                                        <Input
                                                            type="number"
                                                            min={0}
                                                            max={100}
                                                            value={editForm.progress !== undefined ? editForm.progress : 0}
                                                            onChange={e => setEditForm({ ...editForm, progress: Math.min(100, Math.max(0, parseInt(e.target.value) || 0)) })}
                                                            className="h-9 text-xs"
                                                        />
                                                    </div>
                                                </div>

                                                {/* 开始时间 */}
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                                                        <Calendar className="w-3 h-3" /> 开始时间
                                                    </label>
                                                    <Input
                                                        type="datetime-local"
                                                        value={toDatetimeLocal(editForm.start_time)}
                                                        onChange={e => setEditForm({ ...editForm, start_time: e.target.value })}
                                                        className="h-9 text-sm"
                                                    />
                                                </div>

                                                {/* 截止时间 */}
                                                <div className="space-y-1.5">
                                                    <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                                                        <Clock className="w-3 h-3" /> 截止时间
                                                    </label>
                                                    <Input
                                                        type="datetime-local"
                                                        value={toDatetimeLocal(editForm.due_date)}
                                                        onChange={e => setEditForm({ ...editForm, due_date: e.target.value })}
                                                        className="h-9 text-sm"
                                                    />
                                                </div>
                                            </div>

                                            {/* 进展情况 (New) */}
                                            <div className="space-y-1.5">
                                                <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                                                    <Edit2 className="w-3 h-3" /> 进展情况
                                                </label>
                                                <Textarea
                                                    value={editForm.progress_notes || ''}
                                                    onChange={e => setEditForm({ ...editForm, progress_notes: e.target.value })}
                                                    className="min-h-[60px] text-sm resize-none"
                                                    placeholder="记录最新进展..."
                                                />
                                            </div>

                                            {/* 详细描述 */}
                                            <div className="space-y-1.5">
                                                <label className="text-xs font-medium text-muted-foreground">详细描述</label>
                                                <Textarea
                                                    value={editForm.description || ''}
                                                    onChange={e => setEditForm({ ...editForm, description: e.target.value })}
                                                    className="min-h-[80px] text-sm resize-none"
                                                    placeholder="添加更多备注信息..."
                                                />
                                            </div>

                                            <div className="flex justify-end gap-3 pt-2 border-t">
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    className="h-8 text-muted-foreground"
                                                    onClick={() => setEditingId(null)}
                                                >
                                                    取消
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    className="h-8 px-4"
                                                    onClick={handleSave}
                                                    disabled={isUpdating}
                                                >
                                                    {isUpdating ? (
                                                        <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                                                    ) : (
                                                        <Save className="w-3.5 h-3.5 mr-1.5" />
                                                    )}
                                                    {isUpdating ? '保存中...' : '保存更改'}
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Expanded Details - View Mode */}
                                {isExpanded && !isEditing && (
                                    <div className="px-3 pb-3 pt-0 animate-in slide-in-from-top-1 duration-200">
                                        <div className="space-y-3 bg-muted/30 p-4 rounded-xl border border-border/50">
                                            {/* 进展备注 */}
                                            {todo.progress_notes && (
                                                <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap">
                                                    {todo.progress_notes}
                                                </p>
                                            )}

                                            {/* 详细描述 */}
                                            {todo.description && (
                                                <div className="space-y-1">
                                                    <div className="text-xs font-medium text-muted-foreground">描述</div>
                                                    <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap">
                                                        {todo.description}
                                                    </p>
                                                </div>
                                            )}

                                            {/* 如果没有任何内容则显示提示 */}
                                            {!todo.progress_notes && !todo.description && (
                                                <p className="text-xs text-muted-foreground text-center py-2">暂无详情</p>
                                            )}
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
