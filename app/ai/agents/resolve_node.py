"""待办实体解析节点（中文注释）。

在确认操作之前，解析模糊的待办标识为具体的 todo_id。
解决"先确认后解析"导致的歧义问题。
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Any

from langchain_core.messages import AIMessage

from app.db.session import get_db_context
from app.repositories.todo_repository import todo_repo
from app.ai.utils.state_helpers import get_user_id_optional
from app.ai.state import TodoAgentState

logger = logging.getLogger(__name__)


def resolve_entity(state: TodoAgentState) -> Dict:
    """实体解析节点 - 在确认前将模糊标识解析为具体 ID。
    
    处理逻辑：
    1. 如果操作已有 todo_id，直接放行。
    2. 如果操作是 create/query/summarize，直接放行。
    3. 对于 update/delete/complete 操作：
       - 使用 title/keyword 模糊搜索。
       - 匹配 0 个：设置 needs_clarification，提示找不到。
       - 匹配 1 个：将 todo_id 写入 pending_operation。
       - 匹配多个：设置 needs_clarification，列出选项供选择。
       
    Returns:
        Dict: 增量更新字典（LangGraph 最佳实践）
    """
    logger.info("=== resolve_entity 节点 ===")
    
    pending_op = state.get("pending_operation")
    
    # 无操作，直接放行（返回空更新）
    if not pending_op:
        logger.info("无待处理操作，跳过实体解析")
        return {}
    
    # 深拷贝以避免修改原始 state
    pending_op = dict(pending_op)
    action = pending_op.get("action", "")
    data = dict(pending_op.get("data", {}))
    
    # 不需要解析的操作类型
    # 注：batch_create 已废弃（2026-02-01），系统不支持批量创建意图
    skip_actions = ["create", "query", "summarize", "clarify", "constraint"]
    if action in skip_actions:
        logger.info(f"操作 '{action}' 无需实体解析，跳过")
        return {}
    
    # 已有 todo_id，无需解析
    if data.get("todo_id"):
        logger.info(f"已有 todo_id={data.get('todo_id')}，跳过解析")
        return {}
    
    # 需要解析的操作：update, delete, complete, merge
    needs_resolution_actions = ["update", "delete", "complete", "merge"]
    if action not in needs_resolution_actions:
        logger.info(f"操作 '{action}' 不在需解析列表中，跳过")
        return {}
    
    # 获取用户 ID
    user_id = get_user_id_optional(state, config=None)
    if not user_id:
        logger.warning("无法获取 user_id，跳过实体解析")
        return {}
    
    # 提取搜索关键词
    keyword = data.get("target_title") or data.get("title") or data.get("keyword")
    
    if not keyword:
        # 无关键词，无法搜索
        logger.info("无搜索关键词，设置需澄清")
        pending_op["needs_clarification"] = True
        return {
            "pending_operation": pending_op,
            "pending_clarifications": ["请告诉我要操作哪个待办事项的名称或 ID"]
        }
    
    # 执行模糊搜索
    matches = _find_matching_todos(user_id, keyword)
    
    if len(matches) == 0:
        # 匹配 0 个：提示找不到
        logger.info(f"未找到匹配 '{keyword}' 的待办")
        pending_op["needs_clarification"] = True
        return {
            "pending_operation": pending_op,
            "pending_clarifications": [f"找不到包含 '{keyword}' 的待办事项，请确认名称或直接告诉我待办 ID"],
            "messages": [AIMessage(
                content=f"❌ 找不到包含「{keyword}」的待办事项。\n\n请检查名称是否正确，或者直接告诉我待办的 ID。"
            )]
        }
    
    elif len(matches) == 1:
        # 匹配 1 个：成功解析
        matched_todo = matches[0]
        logger.info(f"成功解析: '{keyword}' -> #{matched_todo['id']} {matched_todo['title']}")
        
        # 将解析结果写入 pending_operation（使用副本）
        data["todo_id"] = matched_todo["id"]
        data["resolved_title"] = matched_todo["title"]
        pending_op["data"] = data
        pending_op["needs_clarification"] = False
        
        return {"pending_operation": pending_op}
    
    else:
        # 匹配多个：列出选项供选择
        logger.info(f"找到 {len(matches)} 个匹配 '{keyword}' 的待办，需要用户选择")
        
        options_text = "\n".join([
            f"  {i+1}. [{m['id']}] {m['title']}" 
            for i, m in enumerate(matches[:5])
        ])
        
        pending_op["needs_clarification"] = True
        pending_op["disambiguation_options"] = matches[:5]
        
        return {
            "pending_operation": pending_op,
            "pending_clarifications": ["请选择具体是哪一个待办"],
            "messages": [AIMessage(
                content=f"找到 {len(matches)} 个包含「{keyword}」的待办，请选择具体是哪一个：\n\n{options_text}\n\n请说「第 X 个」或「ID 为 XX 的」。"
            )]
        }


def _find_matching_todos(user_id: int, keyword: str, limit: int = 5) -> List[Dict]:
    """根据关键词模糊匹配用户的待办。
    
    Args:
        user_id: 用户 ID
        keyword: 关键词
        limit: 最大返回数量
        
    Returns:
        匹配的待办列表 [{"id": int, "title": str}, ...]
    """
    try:
        with get_db_context() as db:
            todos = todo_repo.list_by_user(
                db, 
                user_id, 
                keyword=keyword, 
                status="pending",
                limit=limit
            )
            return [{"id": t.id, "title": t.title} for t in todos]
    except Exception as e:
        logger.exception(f"模糊匹配待办失败: {e}")
        return []


def route_after_resolve(state: TodoAgentState) -> str:
    """resolve 节点后的路由判断。
    
    Returns:
        - "clarify": 需要澄清（找不到或多个匹配）
        - "confirm": 已解析成功，进入确认
        - "execute": 跳过确认直接执行（如 quick_mode）
    """
    pending_op = state.get("pending_operation")
    
    if not pending_op:
        return "execute"
    
    # 用户已通过规则化确认，直接执行
    if state.get("user_confirmed"):
        logger.info("用户已确认 (user_confirmed=True)，路由到 execute")
        return "execute"
    
    # 需要澄清
    if pending_op.get("needs_clarification"):
        return "clarify"
    
    # 跳过确认
    if pending_op.get("skip_confirmation"):
        return "execute"
    
    # 正常进入确认
    return "confirm"
