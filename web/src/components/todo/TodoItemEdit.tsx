/**
 * 待办项编辑表单组件
 */
"use client"

import React from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    Save,
    Calendar,
    Clock,
    Flag,
    Activity,
    Loader2,
    Edit2,
    X
} from 'lucide-react'
import { Todo } from '@/types/todo'
import { toDatetimeLocal } from './utils'

interface TodoItemEditProps {
    editForm: Partial<Todo>
    isUpdating: boolean
    onUpdateForm: (form: Partial<Todo>) => void
    onSave: () => void
    onCancel: () => void
}

export default function TodoItemEdit({
    editForm,
    isUpdating,
    onUpdateForm,
    onSave,
    onCancel
}: TodoItemEditProps) {
    return (
        <div className="px-3 pb-3 pt-0 animate-in slide-in-from-top-2 duration-200">
            <div className="bg-card p-4 rounded-xl border shadow-sm space-y-4">
                {/* 标题 */}
                <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                        标题 <span className="text-destructive">*</span>
                    </label>
                    <Input
                        value={editForm.title || ''}
                        onChange={e => onUpdateForm({ title: e.target.value })}
                        className="h-9 text-sm font-medium"
                        autoFocus
                    />
                </div>

                {/* 属性网格 - 小屏单列，sm 以上双列 */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    {/* 优先级 */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                            <Flag className="w-3 h-3" /> 优先级
                        </label>
                        <Select
                            value={String(editForm.priority || 2)}
                            onValueChange={(val) => onUpdateForm({ priority: Number(val) as 1 | 2 | 3 })}
                        >
                            <SelectTrigger className="h-9 text-xs">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="1">高优先级</SelectItem>
                                <SelectItem value="2">中优先级</SelectItem>
                                <SelectItem value="3">低优先级</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {/* 进度 */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                            <Activity className="w-3 h-3" /> 进度 (%)
                        </label>
                        <Input
                            type="number"
                            min={0}
                            max={100}
                            value={editForm.progress ?? 0}
                            onChange={e => onUpdateForm({ 
                                progress: Math.min(100, Math.max(0, parseInt(e.target.value) || 0)) 
                            })}
                            className="h-9 text-xs"
                        />
                    </div>

                    {/* 开始时间 */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                            <Calendar className="w-3 h-3" /> 开始时间
                        </label>
                        <Input
                            type="datetime-local"
                            value={toDatetimeLocal(editForm.start_time)}
                            onChange={e => onUpdateForm({ start_time: e.target.value })}
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
                            onChange={e => onUpdateForm({ due_date: e.target.value })}
                            className="h-9 text-sm"
                        />
                    </div>
                </div>

                {/* 进展情况 */}
                <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                        <Edit2 className="w-3 h-3" /> 进展情况
                    </label>
                    <Textarea
                        value={editForm.progress_notes || ''}
                        onChange={e => onUpdateForm({ progress_notes: e.target.value })}
                        className="min-h-[60px] text-sm resize-none"
                        placeholder="记录最新进展..."
                    />
                </div>

                {/* 详细描述 */}
                <div className="space-y-1.5">
                    <label className="text-xs font-medium text-muted-foreground">详细描述</label>
                    <Textarea
                        value={editForm.description || ''}
                        onChange={e => onUpdateForm({ description: e.target.value })}
                        className="min-h-[80px] text-sm resize-none"
                        placeholder="添加更多备注信息..."
                    />
                </div>

                {/* 操作按钮 */}
                <div className="flex justify-end gap-3 pt-2 border-t">
                    <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 text-muted-foreground"
                        onClick={onCancel}
                        disabled={isUpdating}
                    >
                        <X className="w-3.5 h-3.5 mr-1.5" />
                        取消
                    </Button>
                    <Button
                        size="sm"
                        className="h-8 px-4"
                        onClick={onSave}
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
    )
}
