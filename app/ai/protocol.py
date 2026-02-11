"""Agent 通信协议解析模块。

负责处理 Agent 间的隐式通信协议，包括：
1. Handoff 指令: <!--HANDOFF:{...}-->
2. 知识库图片映射: <!--KB_IMAGES:{...}-->
3. 内部状态过滤: JSON 代码块等
"""
import re
import json
import logging
from typing import Optional, Dict, Any, Tuple, List, Set
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage

from app.ai.utils.message_factory import create_ai_message

logger = logging.getLogger(__name__)

class AgentProtocol:
    """协议常量定义"""
    HANDOFF_PATTERN = r'<!--HANDOFF:(\{.*?\})-->'
    KB_IMAGES_PATTERN = r'<!--KB_IMAGES:(\{.*?\})-->'
    IMG_PLACEHOLDER_PATTERN = r'\[IMG-\d+\]'

class HandoffResult(BaseModel):
    """[Phase 2] 标准 Handoff 结果模型。"""
    action: str = Field(default="handoff", description="操作类型")
    target_agent: str = Field(..., description="目标专家 Agent 名称")
    task_description: str = Field(..., description="任务描述与上下文")
    frame: Optional[Dict[str, Any]] = Field(default=None, description="结构化会话帧（可选）")
    turn_act_hint: Optional[str] = Field(default=None, description="回合行为提示（可选）")

class AgentOutputParser:
    """Agent 输出解析器"""
    
    @staticmethod
    def parse_handoff(content: str) -> Optional[Dict[str, Any]]:
        """解析 Handoff 指令 (支持 Regex 和 纯 JSON)"""
        # 1. 优先尝试 Regex (兼容旧协议)
        match = re.search(AgentProtocol.HANDOFF_PATTERN, content)
        if match:
            try:
                data = json.loads(match.group(1))
                return data
            except json.JSONDecodeError:
                logger.warning("Handoff Regex JSON 解析失败")
        
        # 2. 尝试解析纯 JSON (标准化协议)
        # 只有当内容看起来像 JSON 对象时才尝试
        stripped = content.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                data = json.loads(stripped)
                # 简单校验
                if data.get("action") == "handoff":
                    return data
            except json.JSONDecodeError:
                pass
                
        return None

    @staticmethod
    def extract_latest_handoff_from_messages(messages: List[BaseMessage]) -> Optional[Dict[str, Any]]:
        """从消息列表中提取最近一次 handoff 指令（只扫描 ToolMessage）。
        
        说明：
        - 在 ReAct/工具调用链路中，模型可能在调用工具后继续输出一条 AIMessage。
          因此 ToolMessage 不一定是 messages[-1]，需要回溯扫描。
        - 调用方应传入“本轮增量消息”（delta），避免误取历史回合的 handoff。
        """
        if not messages:
            return None
        
        for msg in reversed(messages):
            if not isinstance(msg, ToolMessage):
                continue
            content = str(getattr(msg, "content", ""))
            if not content:
                continue
            handoff = AgentOutputParser.parse_handoff(content)
            if handoff:
                return handoff
        
        return None
    
    @staticmethod
    def parse_handoff_typed(content: str) -> Optional["HandoffResult"]:
        """类型安全的 Handoff 解析（返回 Pydantic 模型）。
        
        相比 parse_handoff，此方法提供：
        1. 返回类型为 HandoffResult，IDE 可直接提示字段
        2. Pydantic 验证确保数据结构正确
        3. 失败时返回 None 而不是抛异常
        """
        data = AgentOutputParser.parse_handoff(content)
        if data is None:
            return None
        
        try:
            return HandoffResult(**data)
        except Exception as e:
            logger.warning(f"HandoffResult 验证失败: {e}")
            return None

    @staticmethod
    def parse_kb_images(content: str) -> Optional[Dict[str, str]]:
        """解析知识库图片映射"""
        match = re.search(AgentProtocol.KB_IMAGES_PATTERN, content)
        if match:
            try:
                data = json.loads(match.group(1))
                return data
            except json.JSONDecodeError:
                logger.warning("KB Images JSON 解析失败")
        return None

    @staticmethod
    def should_filter_content(content: str) -> bool:
        """判断内容是否应该被过滤（不发送给用户）。
        
        只过滤明确属于内部协议的内容，避免误过滤 LLM 的正常回复。
        """
        if not content or not isinstance(content, str):
            return False
        
        stripped = content.strip()
        if not stripped:
            return False
        
        # 1. 纯 JSON - 只过滤包含内部协议字段的 JSON
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                data = json.loads(stripped)
                # 只有包含明确的内部协议字段才过滤
                INTERNAL_KEYS = {"intent", "action", "target_agent", "task_description"}
                if isinstance(data, dict) and data.get("action") == "handoff":
                    return True
                if isinstance(data, dict) and any(k in data for k in INTERNAL_KEYS) and len(data) <= 5:
                    return True
            except (json.JSONDecodeError, TypeError):
                pass
                
        # 2. Markdown JSON 代码块 - 仅当整个内容就是一个代码块时才过滤
        if stripped.startswith("```json") and stripped.endswith("```"):
            return True
            
        # 3. 包含特定内部关键词
        if "<!--HANDOFF:" in stripped:
            return True
            
        return False

class MessageFilter:
    """消息过滤器：用于隔离不同 Agent 的上下文"""
    
    @staticmethod
    def filter_for_tool_whitelist(messages: List[BaseMessage], allowed_tools: Set[str]) -> List[BaseMessage]:
        """
        基于工具白名单过滤消息历史。
        用于防止 Agent A 的工具调用（如 SQL 查询）污染 Agent B 的上下文（导致 400 错误）。
        
        Args:
            messages: 原始消息列表
            allowed_tools: 允许的工具名称集合
            
        Returns:
            过滤后的安全消息列表
        """
        filtered = []
        for msg in messages:
            # A. 工具调用消息 (AIMessage with tool_calls)
            if isinstance(msg, AIMessage) and msg.tool_calls:
                # 过滤不在白名单的工具调用
                safe_calls = [tc for tc in msg.tool_calls if tc.get("name") in allowed_tools]
                
                if not safe_calls:
                    # 如果没有合法的工具调用，但有文本内容，保留文本
                    if msg.content:
                        filtered.append(create_ai_message(msg.content, id=msg.id))
                    continue
                
                # 如果部分工具调用不合法，仅保留合法的
                if len(safe_calls) != len(msg.tool_calls):
                    new_msg = create_ai_message(msg.content, id=msg.id, tool_calls=safe_calls)
                    filtered.append(new_msg)
                else:
                    filtered.append(msg)
                continue
            
            # B. 工具执行结果 (ToolMessage)
            if isinstance(msg, ToolMessage):
                if msg.name not in allowed_tools:
                    continue
            
            filtered.append(msg)
            
        return filtered
