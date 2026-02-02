/**
 * 待办项详情查看组件
 */
"use client"

import React from 'react'
import { Todo } from '@/types/todo'

interface TodoItemViewProps {
    todo: Todo
}

export default function TodoItemView({ todo }: TodoItemViewProps) {
    const hasContent = todo.progress_notes || todo.description

    return (
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

                {/* 无内容提示 */}
                {!hasContent && (
                    <p className="text-xs text-muted-foreground text-center py-2">
                        暂无详情
                    </p>
                )}
            </div>
        </div>
    )
}
