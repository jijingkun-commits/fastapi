/**
 * 待办卡片工具函数
 */
import { format, isToday, isTomorrow, isThisYear } from 'date-fns'
import { zhCN } from 'date-fns/locale'

/**
 * 友好日期格式化
 * - 今天: 今天 HH:mm
 * - 明天: 明天 HH:mm
 * - 今年: MM月dd日 HH:mm
 * - 其他: yyyy-MM-dd HH:mm
 */
export function formatFriendlyDate(dateStr?: string): string {
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
    } catch {
        return dateStr
    }
}

/**
 * 转换为 datetime-local 输入格式 (YYYY-MM-DDThh:mm)
 */
export function toDatetimeLocal(isoStr?: string): string {
    if (!isoStr) return ''
    try {
        if (isoStr.length === 10) return `${isoStr}T09:00`
        return new Date(isoStr).toISOString().slice(0, 16)
    } catch {
        return ''
    }
}

/**
 * 优先级颜色映射
 * - 高: 橙色系 - 醒目但不与删除按钮红色冲突
 * - 中: 黄色系 - 中等优先级，柔和提醒
 * - 低: 灰蓝色系 - 低调不抢眼
 */
export const priorityColors: Record<number, string> = {
    1: 'bg-orange-50 text-orange-700 border-orange-200 hover:bg-orange-100 dark:bg-orange-950/30 dark:text-orange-400 dark:border-orange-900',
    2: 'bg-yellow-50 text-yellow-700 border-yellow-200 hover:bg-yellow-100 dark:bg-yellow-950/30 dark:text-yellow-400 dark:border-yellow-900',
    3: 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100 dark:bg-slate-800/30 dark:text-slate-400 dark:border-slate-700'
}

/**
 * 优先级名称映射
 */
export const priorityNames: Record<number, string> = {
    1: '高',
    2: '中',
    3: '低'
}

/**
 * 检查是否过期
 */
export function isOverdue(dueDate?: string, isCompleted?: boolean): boolean {
    if (!dueDate || isCompleted) return false
    return new Date(dueDate) < new Date()
}
