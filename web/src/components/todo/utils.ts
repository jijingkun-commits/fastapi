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
 */
export const priorityColors: Record<number, string> = {
    1: 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100 dark:bg-red-950/30 dark:text-red-400 dark:border-red-900',
    2: 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100 dark:bg-amber-950/30 dark:text-amber-400 dark:border-amber-900',
    3: 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100 dark:bg-blue-950/30 dark:text-blue-400 dark:border-blue-900'
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
