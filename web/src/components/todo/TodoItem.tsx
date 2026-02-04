/**
 * 单个待办项组件
 */
"use client"

import React, { memo, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Progress } from "@/components/ui/progress"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import {
    CheckCircle,
    Trash2,
    Clock,
    ChevronDown,
    ChevronUp,
    Edit2,
    Repeat,
    Tag
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Todo } from '@/types/todo'
import { formatFriendlyDate, priorityColors, priorityNames, isOverdue } from './utils'
import TodoItemEdit from './TodoItemEdit'
import TodoItemView from './TodoItemView'

interface TodoItemProps {
    todo: Todo
    isSelected: boolean
    isExpanded: boolean
    isEditing: boolean
    editForm: Partial<Todo>
    isUpdating: boolean
    readonly?: boolean
    onSelect: (id: number) => void
    onDoubleClick: (todo: Todo) => void
    onToggleExpand: (id: number) => void
    onStartEdit: (todo: Todo) => void
    onUpdateForm: (form: Partial<Todo>) => void
    onSave: () => void
    onCancelEdit: () => void
    onComplete: (id: number) => void
    onDelete: (id: number) => void
}

function TodoItemComponent({
    todo,
    isSelected,
    isExpanded,
    isEditing,
    editForm,
    isUpdating,
    readonly = false,
    onSelect,
    onDoubleClick,
    onToggleExpand,
    onStartEdit,
    onUpdateForm,
    onSave,
    onCancelEdit,
    onComplete,
    onDelete
}: TodoItemProps) {
    const isCompleted = todo.status === 'done'
    const overdue = isOverdue(todo.due_date, isCompleted)

    const handleClick = useCallback(() => {
        if (!readonly && !isEditing) {
            onSelect(todo.id)
        }
    }, [readonly, isEditing, onSelect, todo.id])

    const handleDoubleClick = useCallback(() => {
        if (!readonly) {
            onDoubleClick(todo)
        }
    }, [readonly, onDoubleClick, todo])

    const handleExpandClick = useCallback((e: React.MouseEvent) => {
        e.stopPropagation()
        onToggleExpand(todo.id)
    }, [onToggleExpand, todo.id])

    return (
        <div
            className={cn(
                "transition-all duration-200 group cursor-pointer border-l-4 border-transparent",
                isSelected && "bg-primary/5 border-l-primary shadow-sm",
                !isSelected && "hover:bg-muted/30",
                isExpanded && "bg-muted/20",
                isEditing && "ring-2 ring-primary/20"
            )}
            onClick={handleClick}
            onDoubleClick={handleDoubleClick}
        >
            {/* 主行 */}
            <div className="flex items-center gap-3 p-3">
                <div className="flex-1 min-w-0">
                    {/* 第一行：标题 + 优先级 + 时间 + 按钮 */}
                    <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                            {/* 标题 - 使用 line-clamp 替代硬编码截断 */}
                            <span 
                                className={cn(
                                    "font-medium text-sm transition-colors line-clamp-1",
                                    isCompleted && "text-muted-foreground line-through decoration-muted-foreground/50"
                                )}
                                title={todo.title}
                            >
                                {todo.title}
                            </span>

                            {/* 重复任务图标 */}
                            {todo.is_recurring && (
                                <span
                                    className="flex items-center text-blue-500 flex-shrink-0"
                                    title={`${todo.recurrence_pattern === 'daily' ? '每日' : todo.recurrence_pattern === 'weekly' ? '每周' : '每月'}重复`}
                                >
                                    <Repeat className="w-3 h-3" />
                                </span>
                            )}

                            {/* 优先级标签 */}
                            <span className={cn(
                                "px-1.5 py-0.5 rounded text-[10px] font-medium border flex-shrink-0",
                                priorityColors[todo.priority]
                            )}>
                                {priorityNames[todo.priority]}
                            </span>

                            {/* 截止时间 */}
                            {todo.due_date && (
                                <span className={cn(
                                    "flex items-center gap-1 text-xs flex-shrink-0",
                                    overdue && "text-destructive font-medium animate-pulse"
                                )}>
                                    <Clock className="w-3 h-3" />
                                    {formatFriendlyDate(todo.due_date)}
                                </span>
                            )}
                        </div>

                        {/* 右侧按钮区 */}
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                            {!readonly && isSelected && (
                                <>
                                    {/* 编辑按钮 - 使用主题色 */}
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        className="h-7 text-xs font-medium px-2.5 text-slate-600 hover:text-slate-900 hover:bg-slate-50 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-800"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            onStartEdit(todo)
                                        }}
                                    >
                                        <Edit2 className="w-3.5 h-3.5 mr-1" />
                                        编辑
                                    </Button>

                                    {/* 完成按钮 - 仅对未完成任务显示 */}
                                    {!isCompleted && (
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="h-7 text-xs font-medium px-2.5 text-emerald-600 border-emerald-200 hover:bg-emerald-50 hover:border-emerald-300 dark:text-emerald-400 dark:border-emerald-800 dark:hover:bg-emerald-950/30"
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                onComplete(todo.id)
                                            }}
                                        >
                                            <CheckCircle className="w-3.5 h-3.5 mr-1" />
                                            完成
                                        </Button>
                                    )}

                                    {/* 删除按钮 - 使用 Popover 确认，统一 outline 样式 */}
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                className="h-7 text-xs font-medium px-2.5 text-rose-500 border-rose-200 hover:bg-rose-50 hover:border-rose-300 dark:text-rose-400 dark:border-rose-800 dark:hover:bg-rose-950/30"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                <Trash2 className="w-3.5 h-3.5 mr-1" />
                                                删除
                                            </Button>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-56 p-3" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
                                            <p className="text-sm mb-3">确定删除这个待办吗？</p>
                                            <div className="flex gap-2 justify-end">
                                                <Button
                                                    size="sm"
                                                    variant="destructive"
                                                    className="h-7 text-xs"
                                                    onClick={() => onDelete(todo.id)}
                                                >
                                                    确认删除
                                                </Button>
                                            </div>
                                        </PopoverContent>
                                    </Popover>
                                </>
                            )}

                            {/* 展开按钮 */}
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6 text-muted-foreground hover:text-primary hover:bg-primary/10"
                                onClick={handleExpandClick}
                            >
                                {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </Button>
                        </div>
                    </div>

                    {/* 第二行：进度条 + 分类标签 */}
                    <div className="mt-1 space-y-1">
                        {/* 进度条 */}
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

                        {/* 描述预览 */}
                        {todo.description && !isExpanded && (
                            <p className="text-xs text-muted-foreground line-clamp-1">
                                {todo.description}
                            </p>
                        )}
                    </div>
                </div>
            </div>

            {/* 展开区域 - 编辑模式 */}
            {isExpanded && isEditing && (
                <TodoItemEdit
                    editForm={editForm}
                    isUpdating={isUpdating}
                    onUpdateForm={onUpdateForm}
                    onSave={onSave}
                    onCancel={onCancelEdit}
                />
            )}

            {/* 展开区域 - 查看模式 */}
            {isExpanded && !isEditing && (
                <TodoItemView todo={todo} />
            )}
        </div>
    )
}

// 使用 memo 优化渲染
export default memo(TodoItemComponent, (prev, next) => {
    return (
        prev.todo === next.todo &&
        prev.isSelected === next.isSelected &&
        prev.isExpanded === next.isExpanded &&
        prev.isEditing === next.isEditing &&
        prev.editForm === next.editForm &&
        prev.isUpdating === next.isUpdating &&
        prev.readonly === next.readonly
    )
})
