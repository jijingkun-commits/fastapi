/**
 * TodoListCard 状态管理 Hook
 * 
 * 使用 useReducer 统一管理组件状态
 */
import { useReducer, useCallback } from 'react'
import { Todo } from '@/types/todo'

// ==================== Types ====================

export interface TodoListState {
    selectedId: number | null
    expandedIds: Set<number>
    editingId: number | null
    editForm: Partial<Todo>
    deleteConfirmId: number | null
    isUpdating: boolean
}

export type TodoListAction =
    | { type: 'SELECT'; id: number }
    | { type: 'DESELECT' }
    | { type: 'TOGGLE_EXPAND'; id: number }
    | { type: 'EXPAND'; id: number }
    | { type: 'START_EDIT'; todo: Todo }
    | { type: 'UPDATE_EDIT_FORM'; form: Partial<Todo> }
    | { type: 'CANCEL_EDIT' }
    | { type: 'CONFIRM_DELETE'; id: number }
    | { type: 'CANCEL_DELETE' }
    | { type: 'SET_UPDATING'; value: boolean }
    | { type: 'RESET' }

// ==================== Reducer ====================

const initialState: TodoListState = {
    selectedId: null,
    expandedIds: new Set(),
    editingId: null,
    editForm: {},
    deleteConfirmId: null,
    isUpdating: false
}

function todoListReducer(state: TodoListState, action: TodoListAction): TodoListState {
    switch (action.type) {
        case 'SELECT':
            return {
                ...state,
                selectedId: state.selectedId === action.id ? null : action.id
            }
        case 'DESELECT':
            return { ...state, selectedId: null }
        case 'TOGGLE_EXPAND': {
            const newExpanded = new Set(state.expandedIds)
            if (newExpanded.has(action.id)) {
                newExpanded.delete(action.id)
            } else {
                newExpanded.add(action.id)
            }
            return { ...state, expandedIds: newExpanded }
        }
        case 'EXPAND': {
            const newExpanded = new Set(state.expandedIds)
            newExpanded.add(action.id)
            return { ...state, expandedIds: newExpanded }
        }
        case 'START_EDIT':
            return {
                ...state,
                editingId: action.todo.id,
                editForm: { ...action.todo },
                expandedIds: new Set(state.expandedIds).add(action.todo.id)
            }
        case 'UPDATE_EDIT_FORM':
            return { ...state, editForm: { ...state.editForm, ...action.form } }
        case 'CANCEL_EDIT':
            return { ...state, editingId: null, editForm: {} }
        case 'CONFIRM_DELETE':
            return { ...state, deleteConfirmId: action.id }
        case 'CANCEL_DELETE':
            return { ...state, deleteConfirmId: null }
        case 'SET_UPDATING':
            return { ...state, isUpdating: action.value }
        case 'RESET':
            return initialState
        default:
            return state
    }
}

// ==================== Hook ====================

export interface UseTodoListStateOptions {
    onSelectionChange?: (todoId: number | null, todo?: Todo) => void
}

export function useTodoListState(todos: Todo[], options?: UseTodoListStateOptions) {
    const [state, dispatch] = useReducer(todoListReducer, initialState)

    // 选择处理
    const handleSelect = useCallback((id: number) => {
        dispatch({ type: 'SELECT', id })
        const todo = todos.find(t => t.id === id)
        const newSelection = state.selectedId === id ? null : id
        options?.onSelectionChange?.(newSelection, todo)
    }, [todos, state.selectedId, options])

    // 展开/折叠
    const toggleExpand = useCallback((id: number) => {
        dispatch({ type: 'TOGGLE_EXPAND', id })
    }, [])

    // 开始编辑
    const startEdit = useCallback((todo: Todo) => {
        dispatch({ type: 'START_EDIT', todo })
    }, [])

    // 更新编辑表单
    const updateEditForm = useCallback((form: Partial<Todo>) => {
        dispatch({ type: 'UPDATE_EDIT_FORM', form })
    }, [])

    // 取消编辑
    const cancelEdit = useCallback(() => {
        dispatch({ type: 'CANCEL_EDIT' })
    }, [])

    // 设置更新状态
    const setUpdating = useCallback((value: boolean) => {
        dispatch({ type: 'SET_UPDATING', value })
    }, [])

    return {
        state,
        dispatch,
        handleSelect,
        toggleExpand,
        startEdit,
        updateEditForm,
        cancelEdit,
        setUpdating
    }
}
