/**
 * 移动端友好的待办确认卡片组件
 * 
 * 特性:
 * - 支持 create / update / delete / complete 操作
 * - 列表形式展示部分信息
 * - 点击展开查看/编辑详情
 * - 响应式设计 (手机/平板/桌面)
 * 
 * 注：batch_create 已废弃（2026-02-01），系统不支持批量创建
 */
'use client'

import React, { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
    CheckCircle,
    XCircle,
    Calendar,
    ChevronDown,
    ChevronUp,
    Edit2,
    AlertCircle,
    Trash2,
    ArrowRight
} from 'lucide-react'

// ==================== Types ====================

interface TodoItem {
    title: string
    time?: string
    priority?: number
    category?: string
    description?: string
}

interface ConfirmationData {
    action: 'create' | 'update' | 'delete' | 'complete'
    data: Record<string, unknown>
    summary?: string
    target_task?: { id: number; title: string }
    diff?: Record<string, { old: unknown; new: unknown }>
}

interface ConfirmationCardProps {
    operation: ConfirmationData
    onConfirm: (data?: Record<string, unknown>) => void
    onCancel: () => void
}

// ==================== Component ====================

export default function ConfirmationCard({
    operation,
    onConfirm,
    onCancel
}: ConfirmationCardProps) {
    const [isExpanded, setIsExpanded] = useState(false)
    const [editedData, setEditedData] = useState<TodoItem | null>(null)

    // 获取待办数据
    const getTodoData = (): TodoItem => {
        return (operation.data as TodoItem) || { title: '' }
    }

    const todo = editedData || getTodoData()

    // 编辑待办
    const handleEdit = (field: string, value: string | number) => {
        setEditedData({ ...todo, [field]: value })
    }

    // 确认操作
    const handleConfirm = () => {
        onConfirm(editedData || operation.data)
    }

    const priorityNames: Record<number, string> = { 1: '高', 2: '中', 3: '低' }
    const priorityColors: Record<number, string> = {
        1: 'bg-red-100 text-red-700 border-red-200',
        2: 'bg-yellow-100 text-yellow-700 border-yellow-200',
        3: 'bg-green-100 text-green-700 border-green-200'
    }

    // 字段翻译
    const translateField = (field: string): string => {
        const map: Record<string, string> = {
            title: '标题', description: '描述', due_date: '截止时间',
            priority: '优先级', category: '分类', progress: '进度', time: '时间'
        }
        return map[field] || field
    }

    // ==================== Update 视图 ====================
    if (operation.action === 'update') {
        const { target_task, diff } = operation
        return (
            <div className="w-full max-w-md mx-auto">
                <Card className="border-2 border-[#2F6868] bg-[#E8F4F4]/50">
                    <CardContent className="p-4 space-y-4">
                        <div className="flex items-center gap-2 border-b border-[#A8D4D4] pb-2">
                            <Edit2 className="h-5 w-5 text-[#2F6868]" />
                            <div className="font-semibold">确认更新</div>
                        </div>

                        <div className="text-sm">
                            <span className="text-gray-500">目标任务：</span>
                            <span className="font-medium ml-1">
                                {target_task?.id ? `#${target_task.id} ` : ''}
                                {target_task?.title || (operation.data.title as string) || '未知任务'}
                            </span>
                        </div>

                        {diff && Object.keys(diff).length > 0 ? (
                            <div className="space-y-2 bg-white rounded-md p-3 border">
                                {Object.entries(diff).map(([field, change]) => (
                                    <div key={field} className="grid grid-cols-[80px_1fr] gap-2 text-sm items-center">
                                        <span className="text-gray-500 font-medium text-right">
                                            {translateField(field)}:
                                        </span>
                                        <div className="flex items-center gap-1.5 flex-wrap">
                                            {change.old !== undefined && change.old !== null && (
                                                <>
                                                    <span className="line-through text-gray-400">{String(change.old)}</span>
                                                    <ArrowRight className="h-3 w-3 text-gray-400" />
                                                </>
                                            )}
                                            <span className="text-[#2F6868] font-medium">{String(change.new)}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="space-y-2 bg-white rounded-md p-3 border">
                                {Object.entries(operation.data).filter(([k, v]) => 
                                    v && !['todo_id', 'id', 'resolved_title'].includes(k)
                                ).map(([field, value]) => (
                                    <div key={field} className="grid grid-cols-[80px_1fr] gap-2 text-sm items-center">
                                        <span className="text-gray-500 font-medium text-right">{translateField(field)}:</span>
                                        <span className="text-[#2F6868] font-medium">{String(value)}</span>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className="flex gap-2 pt-2">
                            <Button onClick={() => onConfirm(operation.data)} className="flex-1 bg-[#2F6868] hover:bg-[#245454]">
                                <CheckCircle className="mr-2 h-4 w-4" />确认更新
                            </Button>
                            <Button onClick={onCancel} variant="outline" className="flex-1">
                                <XCircle className="mr-2 h-4 w-4" />取消
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        )
    }

    // ==================== Delete 视图 ====================
    if (operation.action === 'delete') {
        const { target_task } = operation
        return (
            <div className="w-full max-w-md mx-auto">
                <Card className="border-2 border-red-500 bg-red-50/50">
                    <CardContent className="p-4 space-y-4">
                        <div className="flex items-center gap-2 border-b border-red-200 pb-2">
                            <Trash2 className="h-5 w-5 text-red-600" />
                            <div className="font-semibold text-red-700">确认删除</div>
                        </div>

                        <div className="flex items-start gap-2 bg-red-100 rounded-md p-3">
                            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-red-700">
                                此操作不可恢复，请确认是否要删除该待办任务。
                            </div>
                        </div>

                        <div className="py-2 text-center bg-white rounded-md border">
                            <div className="text-sm text-gray-600 mb-1">即将删除任务</div>
                            <div className="font-bold text-lg">
                                {target_task?.id ? `#${target_task.id} ` : ''}
                                {target_task?.title || (operation.data.title as string) || '未知任务'}
                            </div>
                        </div>

                        <div className="flex gap-2 pt-2">
                            <Button onClick={() => onConfirm(operation.data)} variant="destructive" className="flex-1">
                                <Trash2 className="mr-2 h-4 w-4" />确认删除
                            </Button>
                            <Button onClick={onCancel} variant="outline" className="flex-1">
                                <XCircle className="mr-2 h-4 w-4" />取消
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        )
    }

    // ==================== Complete 视图 ====================
    if (operation.action === 'complete') {
        const { target_task } = operation
        return (
            <div className="w-full max-w-md mx-auto">
                <Card className="border-2 border-emerald-500 bg-emerald-50/50">
                    <CardContent className="p-4 space-y-4">
                        <div className="flex items-center gap-2 border-b border-emerald-200 pb-2">
                            <CheckCircle className="h-5 w-5 text-emerald-600" />
                            <div className="font-semibold text-emerald-700">确认完成</div>
                        </div>

                        <div className="py-4 text-center bg-white rounded-md border">
                            <div className="text-sm text-gray-600 mb-2">即将完成任务</div>
                            <div className="font-bold text-lg text-emerald-700">
                                {target_task?.id ? `#${target_task.id} ` : ''}
                                {target_task?.title || (operation.data.title as string) || '未知任务'}
                            </div>
                            <div className="mt-3 text-3xl">🎉</div>
                        </div>

                        <div className="flex gap-2 pt-2">
                            <Button onClick={() => onConfirm(operation.data)} className="flex-1 bg-emerald-600 hover:bg-emerald-700">
                                <CheckCircle className="mr-2 h-4 w-4" />确认完成
                            </Button>
                            <Button onClick={onCancel} variant="outline" className="flex-1">
                                <XCircle className="mr-2 h-4 w-4" />取消
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        )
    }

    // ==================== Create 视图（单个待办创建）====================
    return (
        <div className="w-full max-w-md mx-auto">
            <Card className="border-2 border-[#2F6868] bg-[#E8F4F4]/50 backdrop-blur-xl">
                <CardContent className="p-4 space-y-3">
                    {/* 头部 */}
                    <div className="flex items-center gap-2 pb-2 border-b">
                        <CheckCircle className="h-5 w-5 text-[#2F6868]" />
                        <h3 className="font-semibold text-base">待创建</h3>
                    </div>

                    {/* 待办卡片 */}
                    <div className="border rounded-lg border-[#2F6868] bg-[#E8F4F4]">
                        {/* 列表项头部 */}
                        <div className="p-3 flex items-center gap-3">
                            <div className="flex-1 min-w-0" onClick={() => setIsExpanded(!isExpanded)}>
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <div className="font-medium text-sm truncate">
                                            {todo.title || '未命名待办'}
                                        </div>
                                        <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                                            {todo.time && (
                                                <span className="flex items-center gap-1">
                                                    <Calendar className="h-3 w-3" />
                                                    {todo.time}
                                                </span>
                                            )}
                                            <Badge
                                                variant="outline"
                                                className={`text-xs h-5 ${priorityColors[todo.priority as number] || priorityColors[2]}`}
                                            >
                                                {priorityNames[todo.priority as number] || '中'}
                                            </Badge>
                                        </div>
                                    </div>

                                    {/* 展开按钮 */}
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            setIsExpanded(!isExpanded)
                                        }}
                                        className="p-1 hover:bg-gray-100 rounded"
                                    >
                                        {isExpanded ? (
                                            <ChevronUp className="h-4 w-4 text-gray-500" />
                                        ) : (
                                            <ChevronDown className="h-4 w-4 text-gray-500" />
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* 展开的详情 (可编辑) */}
                        {isExpanded && (
                            <div className="px-3 pb-3 pt-0 space-y-3 border-t bg-gray-50/50">
                                {/* 标题编辑 */}
                                <div>
                                    <label className="text-xs font-medium text-gray-500 mb-1 block">标题</label>
                                    <Input
                                        value={todo.title || ''}
                                        onChange={(e) => handleEdit('title', e.target.value)}
                                        className="h-8 text-sm"
                                        placeholder="待办标题"
                                    />
                                </div>

                                {/* 时间编辑 */}
                                <div>
                                    <label className="text-xs font-medium text-gray-500 mb-1 block">截止时间</label>
                                    <Input
                                        value={todo.time || ''}
                                        onChange={(e) => handleEdit('time', e.target.value)}
                                        className="h-8 text-sm"
                                        placeholder="YYYY-MM-DD HH:MM"
                                    />
                                </div>

                                {/* 描述 */}
                                {todo.description && (
                                    <div>
                                        <label className="text-xs font-medium text-gray-500 mb-1 block">描述</label>
                                        <div className="text-sm text-gray-700 p-2 bg-white rounded border">
                                            {todo.description}
                                        </div>
                                    </div>
                                )}

                                {/* 提示 */}
                                {!todo.time && (
                                    <div className="flex items-start gap-2 p-2 rounded bg-amber-50 border border-amber-200">
                                        <AlertCircle className="h-4 w-4 text-amber-600 mt-0.5" />
                                        <div className="text-xs text-amber-700">
                                            未设置截止时间, 默认为早上9点
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* 底部操作按钮 */}
                    <div className="flex gap-2 pt-2">
                        <Button
                            onClick={handleConfirm}
                            className="flex-1 bg-[#2F6868] hover:bg-[#245454]"
                        >
                            <CheckCircle className="mr-2 h-4 w-4" />
                            确认创建
                        </Button>
                        <Button
                            onClick={onCancel}
                            variant="outline"
                            className="flex-1"
                        >
                            <XCircle className="mr-2 h-4 w-4" />
                            取消
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
