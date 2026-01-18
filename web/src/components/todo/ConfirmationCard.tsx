/**
 * 移动端友好的待办确认卡片组件
 * 
 * 特性:
 * - 列表形式展示部分信息
 * - 点击展开查看/编辑详情
 * - 复选框支持批量操作
 * - 响应式设计 (手机/平板/桌面)
 */
'use client'

import React, { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
    CheckCircle,
    XCircle,
    Calendar,
    ChevronDown,
    ChevronUp,
    Edit2,
    AlertCircle
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
    action: 'create' | 'batch_create' | 'delete' | 'batch_complete'
    data: Record<string, any>
}

interface ConfirmationCardProps {
    operation: ConfirmationData
    onConfirm: (data?: Record<string, any>) => void
    onCancel: () => void
}

// ==================== Component ====================

export default function ConfirmationCard({
    operation,
    onConfirm,
    onCancel
}: ConfirmationCardProps) {
    const [selectedItems, setSelectedItems] = useState<Set<number>>(new Set())
    const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set())
    const [editingItems, setEditingItems] = useState<Map<number, TodoItem>>(new Map())

    // 获取待办列表
    const getTodoList = (): TodoItem[] => {
        if (operation.action === 'batch_create') {
            return operation.data.todos || []
        } else if (operation.action === 'create') {
            return [operation.data as TodoItem]
        }
        return []
    }

    const todos = getTodoList()
    const isBatch = todos.length > 1

    // 切换选中状态
    const toggleSelect = (index: number) => {
        const newSelected = new Set(selectedItems)
        if (newSelected.has(index)) {
            newSelected.delete(index)
        } else {
            newSelected.add(index)
        }
        setSelectedItems(newSelected)
    }

    // 全选/取消全选
    const toggleSelectAll = () => {
        if (selectedItems.size === todos.length) {
            setSelectedItems(new Set())
        } else {
            setSelectedItems(new Set(todos.map((_, i) => i)))
        }
    }

    // 切换展开状态
    const toggleExpand = (index: number) => {
        const newExpanded = new Set(expandedItems)
        if (newExpanded.has(index)) {
            newExpanded.delete(index)
        } else {
            newExpanded.add(index)
        }
        setExpandedItems(newExpanded)
    }

    // 编辑待办
    const handleEdit = (index: number, field: string, value: any) => {
        const newEditing = new Map(editingItems)
        const current = newEditing.get(index) || todos[index]
        newEditing.set(index, { ...current, [field]: value })
        setEditingItems(newEditing)
    }

    // 确认操作
    const handleConfirm = () => {
        if (isBatch) {
            // 批量操作: 只确认选中的
            const selectedTodos = todos.filter((_, i) => selectedItems.has(i))
                .map((todo, i) => editingItems.get(i) || todo)
            onConfirm({ ...operation.data, todos: selectedTodos })
        } else {
            // 单个操作
            const editedData = editingItems.get(0) || operation.data
            onConfirm(editedData)
        }
    }

    const priorityNames = { 1: '高', 2: '中', 3: '低' }
    const priorityColors = {
        1: 'bg-red-100 text-red-700 border-red-200',
        2: 'bg-yellow-100 text-yellow-700 border-yellow-200',
        3: 'bg-green-100 text-green-700 border-green-200'
    }

    return (
        <div className="w-full max-w-2xl mx-auto">
            <Card className="border-2 border-blue-500 bg-blue-50/50 backdrop-blur-xl">
                <CardContent className="p-4 space-y-3">
                    {/* 头部 */}
                    <div className="flex items-center justify-between pb-2 border-b">
                        <div className="flex items-center gap-2">
                            <CheckCircle className="h-5 w-5 text-blue-600" />
                            <h3 className="font-semibold text-base">
                                {isBatch ? `待创建 (${todos.length}个)` : '待创建'}
                            </h3>
                        </div>
                        {isBatch && (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={toggleSelectAll}
                                className="h-7 text-xs"
                            >
                                {selectedItems.size === todos.length ? '取消全选' : '全选'}
                            </Button>
                        )}
                    </div>

                    {/* 待办列表 */}
                    <div className="space-y-2">
                        {todos.map((todo, index) => {
                            const isExpanded = expandedItems.has(index)
                            const isSelected = selectedItems.has(index)
                            const editedTodo = editingItems.get(index) || todo

                            return (
                                <div
                                    key={index}
                                    className={`border rounded-lg transition-all ${isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white'
                                        }`}
                                >
                                    {/* 列表项头部 (始终可见) */}
                                    <div className="p-3 flex items-center gap-3">
                                        {/* 复选框 (批量模式) */}
                                        {isBatch && (
                                            <Checkbox
                                                checked={isSelected}
                                                onCheckedChange={() => toggleSelect(index)}
                                                className="mt-1"
                                            />
                                        )}

                                        {/* 主要信息 */}
                                        <div className="flex-1 min-w-0" onClick={() => toggleExpand(index)}>
                                            <div className="flex items-start justify-between gap-2">
                                                <div className="flex-1 min-w-0">
                                                    <div className="font-medium text-sm truncate">
                                                        {editedTodo.title || '未命名待办'}
                                                    </div>
                                                    <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                                                        {editedTodo.time && (
                                                            <span className="flex items-center gap-1">
                                                                <Calendar className="h-3 w-3" />
                                                                {editedTodo.time}
                                                            </span>
                                                        )}
                                                        <Badge
                                                            variant="outline"
                                                            className={`text-xs h-5 ${priorityColors[editedTodo.priority as keyof typeof priorityColors] || priorityColors[2]}`}
                                                        >
                                                            {priorityNames[editedTodo.priority as keyof typeof priorityNames] || '中'}
                                                        </Badge>
                                                    </div>
                                                </div>

                                                {/* 展开按钮 */}
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        toggleExpand(index)
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
                                                    value={editedTodo.title || ''}
                                                    onChange={(e) => handleEdit(index, 'title', e.target.value)}
                                                    className="h-10 text-sm"
                                                    placeholder="待办标题"
                                                />
                                            </div>

                                            {/* 时间编辑 */}
                                            <div>
                                                <label className="text-xs font-medium text-gray-500 mb-1 block">截止时间</label>
                                                <Input
                                                    value={editedTodo.time || ''}
                                                    onChange={(e) => handleEdit(index, 'time', e.target.value)}
                                                    className="h-10 text-sm"
                                                    placeholder="YYYY-MM-DD HH:MM"
                                                />
                                            </div>

                                            {/* 描述 */}
                                            {editedTodo.description && (
                                                <div>
                                                    <label className="text-xs font-medium text-gray-500 mb-1 block">描述</label>
                                                    <div className="text-sm text-gray-700 p-2 bg-white rounded border">
                                                        {editedTodo.description}
                                                    </div>
                                                </div>
                                            )}

                                            {/* 提示 */}
                                            {!editedTodo.time && (
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
                            )
                        })}
                    </div>

                    {/* 底部操作按钮 */}
                    <div className="flex gap-2 pt-2">
                        <Button
                            onClick={handleConfirm}
                            disabled={isBatch && selectedItems.size === 0}
                            className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
                        >
                            <CheckCircle className="mr-2 h-4 w-4" />
                            {isBatch
                                ? `确认创建 (${selectedItems.size}/${todos.length})`
                                : '确认创建'
                            }
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
