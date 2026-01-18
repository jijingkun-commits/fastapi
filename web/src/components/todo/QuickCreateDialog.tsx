/**
 * 快速创建待办对话框
 * 
 * 提供表单填写界面,直接调用API创建待办,绕过Agent确认流程
 */
'use client'

import React, { useState } from 'react'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Plus, Calendar, Tag, AlertCircle } from 'lucide-react'
import { apiFetch } from '@/lib/backend'
import { toast } from 'sonner'

// ==================== Types ====================

interface QuickCreateDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    onSuccess?: () => void
}

interface TodoFormData {
    title: string
    description: string
    priority: number
    category: string
    due_date: string
}

// ==================== Component ====================

export default function QuickCreateDialog({
    open,
    onOpenChange,
    onSuccess
}: QuickCreateDialogProps) {
    const [formData, setFormData] = useState<TodoFormData>({
        title: '',
        description: '',
        priority: 2,
        category: '',
        due_date: ''
    })
    const [isSubmitting, setIsSubmitting] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!formData.title.trim()) {
            toast.error('请输入待办标题')
            return
        }

        setIsSubmitting(true)

        try {
            const response = await apiFetch('/api/v1/todos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: formData.title,
                    description: formData.description || undefined,
                    priority: formData.priority,
                    category: formData.category || undefined,
                    due_date: formData.due_date || undefined
                })
            })

            if (!response.ok) {
                throw new Error('创建失败')
            }

            toast.success('✅ 待办创建成功!')

            // 重置表单
            setFormData({
                title: '',
                description: '',
                priority: 2,
                category: '',
                due_date: ''
            })

            // 关闭对话框
            onOpenChange(false)

            // 触发成功回调
            onSuccess?.()

        } catch (error) {
            console.error('创建待办失败:', error)
            toast.error('创建失败,请稍后重试')
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleFieldChange = (field: keyof TodoFormData, value: any) => {
        setFormData(prev => ({ ...prev, [field]: value }))
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px] p-0 overflow-hidden">
                {/* 渐变头部 */}
                <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-6 text-white">
                    <DialogTitle className="text-2xl font-bold flex items-center gap-2">
                        <Plus className="h-6 w-6" />
                        快速创建
                    </DialogTitle>
                    <p className="text-sm opacity-90 mt-1">立即添加新待办任务</p>
                </div>

                {/* 表单内容 */}
                <form onSubmit={handleSubmit} className="p-6 space-y-5">
                    {/* 标题 */}
                    <div className="space-y-2">
                        <Label htmlFor="title" className="text-sm font-medium flex items-center gap-1">
                            标题 <span className="text-red-500">*</span>
                        </Label>
                        <Input
                            id="title"
                            value={formData.title}
                            onChange={(e) => handleFieldChange('title', e.target.value)}
                            placeholder="例如: 完成项目报告"
                            required
                            className="text-base"
                            autoFocus
                        />
                    </div>

                    {/* 描述 */}
                    <div className="space-y-2">
                        <Label htmlFor="description" className="text-sm font-medium">
                            描述 <span className="text-gray-400 text-xs">(可选)</span>
                        </Label>
                        <Textarea
                            id="description"
                            value={formData.description}
                            onChange={(e) => handleFieldChange('description', e.target.value)}
                            placeholder="添加更多细节..."
                            rows={3}
                            className="resize-none"
                        />
                    </div>

                    {/* 优先级和分类 */}
                    <div className="grid grid-cols-2 gap-4">
                        {/* 优先级 */}
                        <div className="space-y-2">
                            <Label htmlFor="priority" className="text-sm font-medium flex items-center gap-1">
                                <AlertCircle className="h-3.5 w-3.5" />
                                优先级
                            </Label>
                            <select
                                id="priority"
                                value={formData.priority}
                                onChange={(e) => handleFieldChange('priority', Number(e.target.value))}
                                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            >
                                <option value={1}>🔴 高</option>
                                <option value={2}>🟡 中</option>
                                <option value={3}>🟢 低</option>
                            </select>
                        </div>

                        {/* 分类 */}
                        <div className="space-y-2">
                            <Label htmlFor="category" className="text-sm font-medium flex items-center gap-1">
                                <Tag className="h-3.5 w-3.5" />
                                分类
                            </Label>
                            <Input
                                id="category"
                                value={formData.category}
                                onChange={(e) => handleFieldChange('category', e.target.value)}
                                placeholder="工作/生活/学习"
                            />
                        </div>
                    </div>

                    {/* 截止时间 */}
                    <div className="space-y-2">
                        <Label htmlFor="due_date" className="text-sm font-medium flex items-center gap-1">
                            <Calendar className="h-3.5 w-3.5" />
                            截止时间 <span className="text-gray-400 text-xs">(可选)</span>
                        </Label>
                        <Input
                            id="due_date"
                            type="datetime-local"
                            value={formData.due_date}
                            onChange={(e) => handleFieldChange('due_date', e.target.value)}
                        />
                    </div>

                    {/* 提交按钮 */}
                    <div className="flex gap-3 pt-2">
                        <Button
                            type="submit"
                            disabled={isSubmitting}
                            className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
                        >
                            {isSubmitting ? (
                                <>
                                    <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                    创建中...
                                </>
                            ) : (
                                <>
                                    <Plus className="mr-2 h-4 w-4" />
                                    立即创建
                                </>
                            )}
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={isSubmitting}
                        >
                            取消
                        </Button>
                    </div>
                </form>
            </DialogContent>
        </Dialog>
    )
}

// ==================== FAB Button ====================

/**
 * 浮动操作按钮 (Floating Action Button)
 */
export function QuickCreateFAB({ onClick }: { onClick: () => void }) {
    return (
        <Button
            onClick={onClick}
            className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-2xl bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 hover:scale-110 transition-all duration-200 z-50"
            aria-label="快速创建待办"
        >
            <Plus className="h-6 w-6" />
        </Button>
    )
}
