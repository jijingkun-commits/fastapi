"""Image Logic Fixer (中文注释).

此模块用于在对话保存到数据库之前，检查并修复 AI 消息中可能缺失的图片链接。
即使 LLM 忘记在回复中包含图片的 Markdown 链接，只要工具调用成功并返回了图片 URL，
此逻辑就会自动将其追加到 AI 的最后一条回复中。
"""
import json
import logging
import re
from typing import Sequence, List, Set

from langchain_core.messages import BaseMessage, AIMessage, ToolMessage, HumanMessage

logger = logging.getLogger(__name__)

def fix_missing_image_links(messages: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """检查并修复缺失的图片链接。
    
    遍历消息列表：
    1. 从 ToolMessage 中提取成功生成的图片 URL。
    2. 检查最后的 AIMessage 是否已经包含了这些 URL。
    3. 如果缺失，将图片 Markdown 链接追加到 AIMessage 内容末尾。
    
    Args:
        messages: 完整的消息历史列表
        
    Returns:
        修复后的消息列表（如果没有修改，可能返回原列表，但建议视为新列表）
    """
    if not messages:
        return messages

    # 1. 收集所有工具生成并在 ToolMessage 中存在的图片 URL
    generated_images: Set[str] = set()
    
    # 只需要关注该轮对话中的 ToolMessage
    # 但为了简单起见，我们扫描所有 ToolMessage。考虑到实际场景，这通常是 postprocess
    # 此时 messages 包含完整历史。其实我们只关心最后一次 AI 回复之前的工具调用。
    # 策略：扫描全量 ToolMessage 也可以，因为 AI 如果已经引用了之前的图，那也没问题。
    # 为了避免把历史久远的图片追加到现在，我们应该只在这个 AI Message *之前* 最近的 ToolMessages 里找?
    # 不，通常 postprocess 是在一轮对话结束时调用。
    # 这一轮对话通常结构是: Human -> AI (call tool) -> Tool -> AI (final answer)
    # 或者: Human -> AI (call tool) -> Tool -> AI (call tool) -> Tool -> AI (final answer)
    # 所以我们收集所有在 *当前* 对话上下文中出现的图片 URL。
    
    # 更严谨的做法：倒序寻找最后一个 AI Message，然后向前寻找 ToolMessage，直到遇到 HumanMessage 或另一个 AI Message
    # 不过简单起见，且考虑到 image_url 是唯一的，我们收集本轮（或整个历史中）所有 ToolMessage 的图片链接
    # 如果最后的 AI Message 没有包含它，就补上。
    # 风险：如果是很久之前的图片，被补到最新的消息里？
    # 解决：通常 postprocess 只处理本次图执行产生的消息增量？
    # 不，langgraph 的 state["messages"] 通常包含完整历史。
    # 因此，我们必须小心只处理 *本轮* 产生的图片。
    
    # 修正策略：
    # 找出最后一个 AIMessage。
    # 找出这个 AIMessage 之前、且在上一条 HumanMessage 之后的所有 ToolMessage。
    
    # 1. 找到最后一个 AIMessage
    last_ai_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            last_ai_idx = i
            break
            
    if last_ai_idx == -1:
        return messages
    
    last_ai_msg = messages[last_ai_idx]
    
    # 2. 从最后一个 AIMessage 向前回溯，收集 ToolMessage，直到遇到 HumanMessage 或另一个 AIMessage (不包含 ToolCall 的 AI Message?)
    # 简单点：向前回溯直到遇到 HumanMessage。这涵盖了本轮对话的所有交互。
    relevant_images: Set[str] = set()
    
    for i in range(last_ai_idx - 1, -1, -1):
        msg = messages[i]
        if isinstance(msg, ToolMessage):
            # 解析 ToolMessage
            content = msg.content
            try:
                # 尝试解析 JSON
                if isinstance(content, str) and (content.strip().startswith("{") or "image_url" in content):
                    data = json.loads(content)
                    # 检查 fig_inter 工具的标准返回格式
                    # { "status": "success", "image_url": "..." }
                    if isinstance(data, dict):
                         img_url = data.get("image_url")
                         status = data.get("status")
                         if img_url and status in ("success", "success_local"):
                             relevant_images.add(img_url)
            except json.JSONDecodeError:
                pass
            except Exception as e:
                logger.warning(f"解析 ToolMessage 出错: {e}")
                
        elif isinstance(msg, HumanMessage):
            # 遇到 HumanMessage，停止回溯
            break
            
    if not relevant_images:
        return messages
        
    # 3. 检查 AIMessage 内容是否包含这些链接
    ai_content = last_ai_msg.content or ""
    
    # 使用简单的字符串包含检查，或者正则
    # 图片 Markdown: ![alt](url)
    
    modifications = []
    
    for url in relevant_images:
        # 检查 URL 是否存在于内容中
        if url not in ai_content:
            modifications.append(url)
            
    if not modifications:
        return messages
        
    # 4. 追加缺失的图片链接
    new_content = ai_content.rstrip()
    for url in modifications:
        logger.info(f"修复: 自动追加缺失的图片链接 {url}")
        new_content += f"\n\n![Generated Image]({url})"
        
    # 创建新的消息对象（避免直接修改原对象，虽然在 python 里对象引用也行，但 langgraph 推荐不可变）
    # 使用 model_copy (如果是 pydantic v2) 或者直接构造新对象
    # Langchain message 是 pydantic v1 usually
    
    # 只要修改 content 即可，其他属性保持不变
    new_ai_msg = AIMessage(
        content=new_content,
        additional_kwargs=last_ai_msg.additional_kwargs,
        response_metadata=last_ai_msg.response_metadata,
        id=last_ai_msg.id,
        name=last_ai_msg.name
    )
    
    # 构造新的消息列表
    new_messages = list(messages)
    new_messages[last_ai_idx] = new_ai_msg
    
    return new_messages
