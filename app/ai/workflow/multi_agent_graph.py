"""多智能体 Supervisor 图定义模块（中文注释）。

本模块实现 Supervisor 模式的多智能体系统：
- Supervisor 负责理解用户意图并路由到合适的专业 Agent
- 问数 Agent: 处理数据查询、分析、可视化
- 知识库 Agent: 处理企业知识库检索问答
- 待办助手 Agent: 处理任务管理相关请求

架构示意（升级版）：
    User -> preprocess -> supervisor -> [experts] -> postprocess -> User
"""
import asyncio
import logging
import re
from typing import Annotated, Sequence, TypedDict, Optional, Literal, Any, Dict, Tuple

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langgraph.types import Command, Send, interrupt
from langgraph.errors import GraphInterrupt
from langgraph.prebuilt import InjectedState
from langgraph.graph import StateGraph, START, END

from app.ai.llm_util import get_llm
from app.db.postgres_checkpoint import get_checkpointer

# 🆕 导入自定义事件工具
from langgraph.config import get_stream_writer
from app.ai.events import emit_status

logger = logging.getLogger(__name__)


# Agent 类型常量定义
class AgentType:
    """专家 Agent 类型枚举。"""
    DATA = "data_expert"
    TODO = "todo_expert"


# Agent 描述映射（仅保留需要多步骤推理的专家）
AGENT_DESCRIPTIONS = {
    AgentType.DATA: """将复杂的多步骤数据分析任务分配给数据专家。

**委派给 data_expert 的场景**（需要多个工具配合）：
- 读取 Excel/CSV 文件并进行多维度分析
- 数据清洗 + 统计分析 + 可视化
- 需要 Python 代码进行复杂计算

**不需要委派的简单任务**（你可以直接处理）：
- 简单 SQL 查询 → 直接用 sql_inter
- 简单绘图 → 直接用 fig_inter
- 知识库搜索 → 直接用 knowledge_search
""",
    AgentType.TODO: """将待办事项管理任务分配给待办助手。

**适用场景**:
- 查询/列出待办: "列出我的待办"、"查看工作类待办"
- 创建待办: "帮我记录一个待办"、"明天10点开会"
- 更新/完成/删除: "完成待办1"、"删除第3个任务"

**重要**: 待办管理需要确认流程，必须委派给 todo_expert。
""",
}


class MultiAgentState(TypedDict):
    """多智能体状态定义。
    
    Attributes:
        messages: 对话消息列表
        user_id: 用户 ID
        thread_id: 对话线程 ID
        enable_thinking: 是否启用深度思考模式
        model_id: 模型标识
        attachment_analysis: 附件分析结果（由 preprocess 节点填充）
        evaluation: 专家工作评估结果（由 evaluate 节点填充）
        iteration_count: 当前迭代次数（防止无限循环）
        _graph_type: Graph 类型标记（用于 resume 时检测）
        pending_handoff: 待处理的委派指令（由 handoff 工具设置）
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: Optional[int]
    thread_id: Optional[str]
    enable_thinking: Optional[bool]
    model_id: Optional[str]
    attachment_analysis: Optional[str]
    evaluation: Optional[str]
    iteration_count: Optional[int]
    thinking_content: Optional[str]
    # 显式标记 Graph 类型，用于 resume 时检测
    _graph_type: Optional[Literal["multi_agent"]]
    # Phase 2: 意图识别字段（借鉴 Flock Intent Recognition）
    detected_intent: Optional[str]
    intent_route: Optional[str]
    # 待处理的委派指令（由 handoff 工具返回值解析）
    pending_handoff: Optional[dict]


# Supervisor 系统提示词（决策树版 - 借鉴 OpenAI Swarm + Anthropic Skills）
SUPERVISOR_PROMPT = """你是一个智能助手 Supervisor，负责理解用户意图并执行或委派任务。

## 决策树

根据用户请求，按以下流程判断：

```
用户请求
    │
    ├─ 简单问候/闲聊？（你好/谢谢/再见）
    │       └─ 是 → 直接回复，不调用任何工具
    │
    ├─ 需要联网实时信息？（天气/新闻/股价/汇率）
    │       └─ 是 → 调用 tavily_search
    │
    ├─ 涉及知识库内容？（公司规定/产品文档/技术资料）
    │       └─ 是 → 调用 knowledge_search
    │
    ├─ 需要数据库查询？（查询表/统计数据）
    │       └─ 是 → 调用 sql_inter
    │
    ├─ 需要绘制图表？（折线图/柱状图/饼图/散点图/几何图形）
    │       └─ 是 → 调用 fig_inter
    │
    ├─ 需要分析图片？（识别图片内容）
    │       └─ 是 → 调用 analyze_image
    │
    ├─ 需要读取上传文件？（查看文件内容）
    │       └─ 是 → 调用 read_uploaded_file
    │
    ├─ 复杂数据分析？（文件处理 + 数据清洗 + 统计 + 可视化）
    │       └─ 是 → 委派给 data_expert（调用 assign_to_data_expert）
    │
    ├─ 待办事项管理？（创建/查询/更新/完成/删除待办）
    │       └─ 是 → 委派给 todo_expert（调用 assign_to_todo_expert）
    │
    └─ 待办确认/补充？（用户简短回复可能是对待办操作的确认）
            │
            └─ 如果上一条 AI 消息包含待办相关内容（如"待办"、"确认"、"创建"等）
                    └─ 是 → 委派给 todo_expert
```

## 重要：待办确认/补充信息识别

当用户发送简短回复或补充信息时，需要检查对话历史：
- 如果上一条 AI 消息涉及待办事项（包含"待办"、"📝"、"确认"、"标题"、"时间"等关键词），则委派给 todo_expert
- **关键**：在 task_description 中必须包含**完整的对话上下文**，包括：
  1. 用户最初的待办请求（如"我明天要去上海"）
  2. AI 之前提取的待办信息（如标题、时间、地点等）
  3. 用户当前的补充/确认内容（如"早上9点，黄河路1001号"）
  
例如，当用户说"早上9点，黄河路1001号"来补充待办信息时，task_description 应该包含：
```
用户最初想创建待办：去上海
- 标题：去上海
- 时间：明天
用户现在补充信息：时间是早上9点，地点是黄河路1001号
请帮用户更新待办信息。
```

## 工具速查

| 工具 | 用途 | 典型请求 |
|------|------|----------|
| tavily_search | 联网搜索 | "上海天气"、"今日新闻" |
| knowledge_search | 知识库检索 | "公司差旅规定"、"产品手册" |
| sql_inter | SQL 查询 | "查询用户表"、"订单统计" |
| fig_inter | 绘制图表 | "画一个饼图"、"画一个圆" |
| analyze_image | 图片分析 | "这张图是什么" |
| read_uploaded_file | 读取文件 | "读取这个文件" |
| assign_to_data_expert | 委派数据分析 | "分析Excel销售趋势" |
| assign_to_todo_expert | 委派待办管理 | "帮我记录一个待办" |

## 执行原则

1. **单工具优先**：能用一个工具解决的，直接调用，不委派，优先使用知识库工具（例如用户只发了一张图片而不带任何文字内容时，那么优先使用 analyze_image 工具，然后提取问题查找知识库）
2. **静默执行**：直接调用工具，不要先输出"让我来..."之类的文字
3. **委派时机**：仅当需要多步骤推理或用户确认流程时，才委派给专家
4. **图片占位符**：knowledge_search 返回的 `[IMG-N]` 占位符**必须原样保留**在回答中

### 图片占位符示例
knowledge_search 返回：
```
【0】账户管理功能... 相关图片: [IMG-0]
【1】转账功能... 相关图片: [IMG-1]
```

你的回答应该包含占位符：
```
账户管理支持电子回单... [IMG-0]
转账功能支持批量操作... [IMG-1]
```

系统会自动将 `[IMG-N]` 替换为实际图片，你只需保留占位符即可。
"""


def _get_common_tools():
    """获取所有专家共享的工具（图片分析、文件读取）。"""
    tools = []
    
    # 图片分析工具
    try:
        from app.ai.tools.vision_tool import analyze_image, is_vision_configured
        if is_vision_configured():
            tools.append(analyze_image)
            logger.debug("共享工具: 已加载 analyze_image")
    except Exception as e:
        logger.warning("Vision 工具加载失败: %s", e)
    
    # 文件读取工具
    try:
        from app.ai.tools.file_tools import read_uploaded_file
        tools.append(read_uploaded_file)
        logger.debug("共享工具: 已加载 read_uploaded_file")
    except Exception as e:
        logger.warning("文件读取工具加载失败: %s", e)
    
    return tools


async def _get_data_tools():
    """获取数据分析工具（包含共享工具 + MCP 工具）。"""
    from app.ai.tools.chatTools import sql_inter, extract_data, python_inter, fig_inter
    from app.core.config import MCP_CHART_ENABLED
    
    tools = _get_common_tools() + [sql_inter, extract_data, python_inter, fig_inter]
    
    # 加载 MCP 图表工具（如果启用）
    if MCP_CHART_ENABLED:
        try:
            from app.ai.mcp import load_chart_tools
            mcp_tools = await load_chart_tools()
            if mcp_tools:
                tools.extend(mcp_tools)
                logger.info("data_expert 已加载 %d 个 MCP 图表工具", len(mcp_tools))
        except Exception as e:
            logger.warning("data_expert MCP 图表工具加载失败: %s", e)
    
    return tools


def _get_supervisor_tools():
    """获取 Supervisor 直接使用的简单工具。
    
    包含：
    - 知识库检索 (knowledge_search)
    - 联网搜索 (tavily_search)
    - SQL 查询 (sql_inter)
    - 绘图 (fig_inter)
    - 图片分析和文件读取（共享工具）
    """
    tools = _get_common_tools()
    
    # SQL 查询和绘图工具
    try:
        from app.ai.tools.chatTools import sql_inter, fig_inter
        tools.extend([sql_inter, fig_inter])
        logger.debug("Supervisor 工具: 已加载 sql_inter, fig_inter")
    except Exception as e:
        logger.warning("Supervisor SQL/绘图工具加载失败: %s", e)
    
    # 知识库搜索工具
    try:
        from app.ai.tools.ragflow_tool import knowledge_search, is_ragflow_configured
        if is_ragflow_configured():
            tools.append(knowledge_search)
            logger.debug("Supervisor 工具: 已加载 knowledge_search")
    except Exception as e:
        logger.warning("Supervisor 知识库工具加载失败: %s", e)
    
    # 联网搜索工具 (TavilySearch)
    try:
        from app.ai.tools.chatTools import search_tool
        if search_tool is not None:
            tools.append(search_tool)
            logger.debug("Supervisor 工具: 已加载 TavilySearch 联网搜索")
    except Exception as e:
        logger.warning("Supervisor 联网搜索工具加载失败: %s", e)
    
    return tools


def _get_data_expert_tools():
    """获取数据专家的完整工具集。
    
    🔧 修复问题6：补全 Data Expert 工具集
    - sql_inter: SQL 查询
    - fig_inter: 绘图
    - extract_data: 文件数据提取
    - python_inter: Python 代码执行
    - 共享工具: 图片分析、文件读取
    """
    tools = _get_common_tools()
    
    try:
        from app.ai.tools.chatTools import sql_inter, fig_inter, extract_data, python_inter
        tools.extend([sql_inter, fig_inter, extract_data, python_inter])
        logger.debug("data_expert 工具: 已加载完整工具集 (sql_inter, fig_inter, extract_data, python_inter)")
    except Exception as e:
        logger.warning("data_expert 工具加载失败: %s", e)
    
    return tools


def _create_task_handoff_tool(agent_name: str, description: str):
    """创建带任务描述的 Handoff 工具。
    
    该工具允许 Supervisor 将任务委派给特定的 Agent，并提供明确的任务描述。
    
    修改说明：
    - 返回 JSON 格式的委派指令，而不是 Command 对象
    - Command 对象会被 ToolNode 序列化为字符串，导致无法正确路由
    - 外层条件边会检测 pending_handoff 字段并路由到对应专家
    """
    
    name = f"assign_to_{agent_name}"
    
    @tool(name, description=description)
    def handoff_tool(
        task_description: Annotated[str, "详细描述下一个专家需要完成的任务，包含所有相关上下文和指令"],
    ) -> str:
        """将任务委派给指定的专家 Agent。返回 JSON 格式的委派指令。"""
        import json
        
        handoff_instruction = {
            "action": "handoff",
            "target_agent": agent_name,
            "task_description": task_description,
        }
        
        return f"<!--HANDOFF:{json.dumps(handoff_instruction, ensure_ascii=False)}-->"
    
    return handoff_tool



async def _preprocess_multimodal(state: MultiAgentState) -> dict:
    """预处理节点：1. 验证消息序列 2. 分析图片/文件内容。
    
    职责：
    - 验证消息完整性，移除不完整的 tool_calls
    - 修复 DeepSeek reasoning_content（如果启用思考模式）
    - 分析用户上传的图片和文件，为 Supervisor 路由提供上下文
    """
    messages = state.get("messages", [])
    if not messages:
        return {}
    
    # 🆕 获取 StreamWriter 用于发送自定义事件
    writer = get_stream_writer()
    
    # 🆕 显式标记 Graph 类型，用于 resume 时检测
    updates = {"_graph_type": "multi_agent"}
    
    # ========== 1. 消息验证与修复 ==========
    # 【补丁代码】修复 DeepSeek Reasoner 的 reasoning_content 缺失问题
    # 详见: app.ai.message_utils.fix_deepseek_reasoning
    # 原因: DeepSeek R1 要求历史消息必须包含 reasoning_content 字段
    # 方案: 已将修复逻辑封装为独立函数 validate_messages，保持代码整洁
    # TODO: 等待 DeepSeek 官方修复此 API 限制后可移除此补丁
    from app.ai.message_utils import validate_messages
    
    enable_thinking = state.get("enable_thinking", False)
    model_id = state.get("model_id")
    
    # 判断是否需要执行 DeepSeek 补丁
    should_fix_reasoning = enable_thinking
    if model_id and ("deepseek" in model_id.lower() or "reasoner" in model_id.lower()):
        should_fix_reasoning = True
    
    # 执行消息验证（包括 DeepSeek 修复）
    original_count = len(messages)
    validated = validate_messages(messages, fix_reasoning=should_fix_reasoning)
    
    if len(validated) != original_count or should_fix_reasoning:
        logger.debug(
            "预处理节点: 消息验证完成, should_fix=%s, 消息数 %d -> %d",
            should_fix_reasoning, original_count, len(validated)
        )
        updates["messages"] = validated
        messages = validated  # 使用验证后的消息继续处理
    
    # ========== 2. 护栏验证（借鉴 OpenAI Agents SDK Guardrails） ==========
    last_msg = messages[-1]
    content = str(getattr(last_msg, "content", ""))
    
    # 只对用户消息执行护栏验证
    from langchain_core.messages import HumanMessage
    if isinstance(last_msg, HumanMessage):
        from app.ai.guardrails import guardrail_runner
        
        passed, sanitized_content, reason = await guardrail_runner.validate_input(content)
        
        if not passed:
            logger.warning("护栏拦截: %s", reason)
            emit_status(writer, message=f"安全检查: {reason}", node="preprocess")
            # 返回拒绝消息（可以选择直接拦截或继续处理）
            # 这里选择记录日志但继续处理，让 LLM 自行决定
        
        if sanitized_content and sanitized_content != content:
            logger.info("护栏: 输入已脱敏处理")
            content = sanitized_content
    
    # 检测是否包含图片 URL（Markdown 格式）
    image_urls = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', content)
    
    if image_urls:
        logger.info("预处理节点: 检测到 %d 张图片，开始分析...", len(image_urls))
        
        # 🆕 发送分析状态给前端
        emit_status(writer, message=f"正在分析 {len(image_urls)} 张图片...", node="preprocess")
        
        try:
            from app.ai.tools.vision_tool import analyze_image, is_vision_configured
            if is_vision_configured():
                # 分析第一张图片
                analysis_result = analyze_image.invoke({"image_url": image_urls[0]})
                logger.info("预处理节点: 图片分析完成 - %s", str(analysis_result)[:100])
                updates["attachment_analysis"] = f"[图片分析结果] {analysis_result}"
                
                # 🆕 发送完成状态
                emit_status(writer, message="图片分析完成", node="preprocess")
        except Exception as e:
            logger.warning("预处理节点: 图片分析失败 - %s", e)
    
    # 检测是否包含文件 URL
    file_patterns = re.findall(r'\[([^\]]+)\]\s+([^\s]+)\s+\(URL:\s*([^)]+)\)', content)
    if file_patterns:
        file_info = [(name, url) for _, name, url in file_patterns]
        logger.info("预处理节点: 检测到 %d 个文件", len(file_info))
        updates["attachment_analysis"] = f"[文件信息] 用户上传了文件: {', '.join([f[0] for f in file_info])}"
    logger.info("jjk-multi-agent: 预处理节点: 更新状态 - %s", updates)
    return updates


async def create_multi_agent_graph(
    checkpointer=None, 
    enable_thinking: bool = False, 
    model_id: str = None
):
    """创建多智能体 Supervisor 图（手动构建）。
    
    架构：
        START -> preprocess -> supervisor -> [data_expert | knowledge_expert | todo_expert]
                                      |
                                      +-> Postprocess -> END
                                      
    注意：专家执行完后会直接返回 END（或者是返回结果给 Supervisor，这里使用 Command(graph=Command.PARENT) 跳转）
    实际上，由于 Handoff 工具使用了 Send()，子 Agent 执行完后，LangGraph 默认行为是结束当前步骤。
    我们需要确保子 Agent 的结果能被 postprocess 捕获（或者直接保存）。
    
    调整：
    专家 Agent 执行完毕后，流程应该汇聚到 postprocess。
    """
    
    # 获取 LLM
    llm = get_llm(force_thinking=enable_thinking, model_id=model_id)
    
    # 1. 创建 Handoff 工具（使用常量定义）
    handoff_tools = [
        _create_task_handoff_tool(agent_type, desc)
        for agent_type, desc in AGENT_DESCRIPTIONS.items()
    ]
    
    # 2. 获取 Supervisor 的简单工具（可以直接调用）
    supervisor_simple_tools = _get_supervisor_tools()
    
    # 3. 创建 Supervisor Agent（handoff 工具 + 简单工具）
    # 使用 create_react_agent，支持工具返回 Command 对象
    supervisor_agent = create_react_agent(
        llm,
        handoff_tools + supervisor_simple_tools,
        prompt=SUPERVISOR_PROMPT,
        name="supervisor",
    )
    
    # 4. 创建 data_expert（仅用于多步骤分析）
    data_agent = create_react_agent(
        llm,
        _get_data_expert_tools(),
        name="data_expert",
        prompt="""你是数据分析专家。

你的工具：
- extract_data: 从文件中提取数据
- python_inter: 执行 Python 代码进行复杂分析

收到任务后，请根据提供的任务描述和上下文进行分析。执行完成后，总结你的工作。
""",
    )
    
    # 5. 创建 todo_expert（使用 TodoGraph）
    from app.ai.workflow.todo_graph import create_todo_graph
    todo_graph_app = create_todo_graph(
        model=llm, 
        enable_thinking=enable_thinking,
        checkpointer=checkpointer 
    )

    # 4. 为专家节点创建流式包装器
    # agent wrapper 内部使用 astream 并通过 emit_token 发送 LLM 输出
    # 这使得 chat_service.py 只需监听 stream_mode="custom"
    def _create_streaming_agent_wrapper(agent, name: str):
        """创建流式 Agent 包装器：捕获 LLM 输出并通过 emit_token 发送。"""
        from app.ai.events import emit_token, emit_thinking, emit_tool_start, emit_tool_end
        from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
        
        async def streaming_wrapper(state, config):
            writer = get_stream_writer()
            final_state = None
            collected_content = []
            
            # kb_images 映射：在收到 ToolMessage 时动态填充
            kb_images = {}
            
            # 记录初始消息数量，用于在 values 模式中只发送新增消息
            input_message_count = len(state.get("messages", []))
            
            try:
                # 🆕 使用 astream + stream_mode="messages" 获取 LLM 流式输出
                # 已发送的 tool_call ID 集合，用于去重
                sent_tool_call_ids = set()
                
                async for mode, chunk in agent.astream(
                    state, 
                    config, 
                    stream_mode=["messages", "values"]
                ):
                    if mode == "messages":
                        # 处理 LLM token 流
                        if isinstance(chunk, tuple) and len(chunk) == 2:
                            msg, metadata = chunk
                            msg_type = type(msg).__name__
                            logger.debug(f"[{name}] messages 模式收到: {msg_type}")
                            
                            # 检测 ToolMessage（工具执行完成）并发送 tool_end 事件
                            if isinstance(msg, ToolMessage):
                                tool_name = getattr(msg, "name", "unknown")
                                tool_content = str(getattr(msg, "content", ""))
                                tool_output = tool_content[:200]  # 截断输出用于日志
                                emit_tool_end(writer, tool_name, tool_output, node=name)
                                
                                import re
                                import json
                                
                                # 检测 HANDOFF 标记（委派指令）
                                # 只在 supervisor 节点执行提前返回，让外层条件边路由到专家
                                handoff_match = re.search(r'<!--HANDOFF:(\{.*?\})-->', tool_content)
                                if handoff_match:
                                    try:
                                        handoff_data = json.loads(handoff_match.group(1))
                                        target_agent = handoff_data.get("target_agent")
                                        logger.info(f"[{name}] 检测到 handoff 指令: target={target_agent}")
                                        
                                        # 只在 supervisor 节点提前返回，其他节点继续处理
                                        if name == "supervisor":
                                            state_update = final_state or {}
                                            state_update["pending_handoff"] = handoff_data
                                            return state_update
                                        # 非 supervisor 节点：跳过 HANDOFF 内容，继续处理
                                    except json.JSONDecodeError:
                                        logger.warning(f"[{name}] handoff JSON 解析失败")
                                
                                # 从 ToolMessage 中提取 kb_images 映射
                                logger.info(f"[{name}] 收到 ToolMessage: name={tool_name}, 长度={len(tool_content)}")
                                kb_images_match = re.search(r'<!--KB_IMAGES:(\{.*?\})-->', tool_content)
                                if kb_images_match:
                                    try:
                                        new_images = json.loads(kb_images_match.group(1))
                                        kb_images.update(new_images)
                                        logger.info(f"[{name}] 从 ToolMessage 提取到 kb_images: {len(new_images)} 个")
                                    except json.JSONDecodeError:
                                        logger.warning(f"[{name}] kb_images JSON 解析失败")
                                else:
                                    logger.info(f"[{name}] ToolMessage 中无 KB_IMAGES 标记")
                                
                                continue
                            
                            # 只处理 AI 消息
                            if not isinstance(msg, (AIMessage, AIMessageChunk)):
                                continue
                            
                            # 提取并发送文本内容
                            content = getattr(msg, "content", "")
                            if content and isinstance(content, str):
                                # 过滤内部输出：跳过 JSON 格式的意图分析结果
                                stripped = content.strip()
                                
                                # 检测纯 JSON
                                if stripped.startswith("{") and stripped.endswith("}"):
                                    try:
                                        import json
                                        json.loads(stripped)
                                        # 是有效 JSON，跳过（内部分析输出）
                                        logger.debug(f"[{name}] 跳过 JSON 格式的内部输出")
                                        continue
                                    except json.JSONDecodeError:
                                        pass  # 不是有效 JSON，继续处理
                                
                                # 检测 markdown 代码块中的 JSON (```json ... ```)
                                if stripped.startswith("```json") and stripped.endswith("```"):
                                    logger.debug(f"[{name}] 跳过 markdown JSON 代码块")
                                    continue
                                
                                # 检测包含 intent 关键字的 JSON 结构（意图分析输出）
                                if '"intent"' in stripped and ('"query"' in stripped or '"create"' in stripped or '"clarify"' in stripped):
                                    logger.debug(f"[{name}] 跳过意图分析 JSON")
                                    continue
                                
                                # 过滤 HANDOFF 标记
                                if "<!--HANDOFF:" in content:
                                    logger.debug(f"[{name}] 跳过 HANDOFF 标记")
                                    continue
                                
                                # 替换占位符为实际图片 Markdown
                                if kb_images:
                                    for idx_str, url in kb_images.items():
                                        placeholder = f"[IMG-{idx_str}]"
                                        if placeholder in content:
                                            markdown_img = f"![参考图片]({url})"
                                            content = content.replace(placeholder, markdown_img)
                                
                                collected_content.append(content)
                                emit_token(writer, content, node=name)
                            
                            # 注意：messages 模式下 tool_calls.args 为空
                            # 工具调用事件在 values 模式下发送（有完整参数）
                            
                            # 提取并发送思考内容
                            additional = getattr(msg, "additional_kwargs", {})
                            reasoning = (
                                additional.get("reasoning_content") or
                                additional.get("thinking_content") or
                                additional.get("thinking")
                            )
                            if reasoning:
                                emit_thinking(writer, reasoning, node=name)
                    
                    elif mode == "values":
                        # values 模式包含完整的 state，从这里获取 tool_calls 参数
                        final_state = chunk
                        
                        # 从 ToolMessage 中提取 kb_images 和 HANDOFF 标记
                        messages = chunk.get("messages", [])
                        for msg in messages:
                            if isinstance(msg, ToolMessage):
                                import re
                                import json
                                tool_content = str(getattr(msg, "content", ""))
                                
                                # 检测 HANDOFF 标记（委派指令）
                                handoff_match = re.search(r'<!--HANDOFF:(\{.*?\})-->', tool_content)
                                if handoff_match:
                                    try:
                                        handoff_data = json.loads(handoff_match.group(1))
                                        target_agent = handoff_data.get("target_agent")
                                        logger.info(f"[{name}] values模式检测到 handoff: target={target_agent}")
                                        
                                        # 更新 final_state 中的 pending_handoff
                                        final_state["pending_handoff"] = handoff_data
                                    except json.JSONDecodeError:
                                        logger.warning(f"[{name}] handoff JSON 解析失败")
                                
                                # 检测 kb_images 标记
                                kb_images_match = re.search(r'<!--KB_IMAGES:(\{.*?\})-->', tool_content)
                                if kb_images_match:
                                    try:
                                        new_images = json.loads(kb_images_match.group(1))
                                        kb_images.update(new_images)
                                        logger.info(f"[{name}] 从 values 模式提取 kb_images: {len(new_images)} 个")
                                        # 发送 kb_images 事件到前端，让前端进行替换
                                        from app.ai.events import emit_kb_images
                                        emit_kb_images(writer, kb_images, node=name)
                                    except json.JSONDecodeError:
                                        pass
                        
                        # 只检查新增的 AI 消息（索引 >= input_message_count），避免发送历史消息
                        new_messages = messages[input_message_count:] if len(messages) > input_message_count else []
                        for new_msg in new_messages:
                            if isinstance(new_msg, AIMessage):
                                # 发送 tool_calls 事件
                                if hasattr(new_msg, 'tool_calls') and new_msg.tool_calls:
                                    for tc in new_msg.tool_calls:
                                        tc_id = tc.get("id")
                                        tool_name = tc.get("name", "")
                                        tool_args = tc.get("args", {})
                                        
                                        # 去重：只发送未发送过的 tool_call
                                        if tc_id and tc_id not in sent_tool_call_ids and tool_name:
                                            sent_tool_call_ids.add(tc_id)
                                            logger.debug(
                                                "发送 tool_start 事件 (from values): name='%s', args=%s",
                                                tool_name, tool_args
                                            )
                                            emit_tool_start(writer, tool_name, tool_args, node=name)
                                else:
                                    # 非 tool_call 的 AIMessage（如 summarize 节点生成的最终输出）
                                    # 只对 todo_expert 发送，避免 supervisor 的消息被重复发送
                                    if name == "todo_expert":
                                        msg_id = getattr(new_msg, 'id', None)
                                        msg_content = getattr(new_msg, 'content', '')
                                        
                                        if msg_id and msg_content and isinstance(msg_content, str):
                                            if msg_id not in sent_tool_call_ids:  # 通过 id 去重
                                                sent_tool_call_ids.add(msg_id)
                                                
                                                # 检查内容是否已发送（避免内容重复）
                                                if msg_content in collected_content:
                                                    logger.debug(f"[{name}] 跳过已发送的内容")
                                                    continue
                                                
                                                # 过滤内部输出（JSON/HANDOFF）
                                                stripped = msg_content.strip()
                                                should_skip = False
                                                
                                                if stripped.startswith("{") and stripped.endswith("}"):
                                                    should_skip = True
                                                if stripped.startswith("```json"):
                                                    should_skip = True
                                                if '"intent"' in stripped:
                                                    should_skip = True
                                                if "<!--HANDOFF:" in stripped:
                                                    should_skip = True
                                                
                                                if not should_skip:
                                                    logger.info(f"[{name}] values 模式发送非流式 AIMessage: {msg_content[:50]}...")
                                                    collected_content.append(msg_content)
                                                    emit_token(writer, msg_content, node=name)
                
                # 🔍 调试日志：打印 LLM 输出统计
                full_output = "".join(collected_content)
                import re
                output_image_count = len(re.findall(r'!\[[^\]]*\]\([^)]+\)', full_output))
                
                logger.debug("="*60)
                logger.debug(f"[{name}] LLM 输出统计:")
                logger.debug(f"  总长度: {len(full_output)} 字符")
                logger.debug(f"  包含图片: {output_image_count} 张")
                logger.debug(f"  输出预览（前 500 字符）:")
                logger.debug(f"  {full_output[:500]}")
                logger.debug("="*60)
                
                return final_state or {}
                
            except GraphInterrupt:
                raise
            except Exception as e:
                logger.exception(f"{name} 节点执行异常: %s", e)
                error_msg = f"抱歉，{name} 在处理任务时遇到内部错误: {str(e)}"
                emit_token(writer, error_msg, node=name)
                return {"messages": [AIMessage(content=error_msg)]}
        
        return streaming_wrapper

    # 5. 定义后处理节点
    def _postprocess(state: MultiAgentState) -> dict:
        """后处理节点：调试日志 + 保存对话到数据库 + 清理缓存。"""
        messages = state.get("messages", [])
        user_id = state.get("user_id")
        thread_id = state.get("thread_id")
        
        # 橙色 ANSI 颜色代码（便于调试）
        ORANGE = "\033[38;5;208m"
        RESET = "\033[0m"
        
        # 打印调试日志
        logger.info(f"{ORANGE}{'='*60}{RESET}")
        logger.info(f"{ORANGE}[多智能体-消息列表] 共 {len(messages)} 条消息:{RESET}")
        for i, msg in enumerate(messages):
            logger.info(f"{ORANGE}  [{i}] {msg}{RESET}")
        logger.info(f"{ORANGE}{'='*60}{RESET}")
        
        # 验证必要参数
        if not thread_id:
            logger.warning("后处理节点: 缺少 thread_id，跳过保存")
            return {}
        
        if not messages:
            logger.warning("后处理节点: 消息为空，跳过保存")
            return {}
        
        # 保存对话到数据库（使用智能图片补充逻辑）
        try:
            from app.db.session import get_db_context
            from app.repositories import chat_repo
            from langchain_core.messages import HumanMessage, AIMessage
            
            # 过滤掉内部 Handoff 消息 (name 不为空的 HumanMessage)
            filtered_messages = [
                msg for msg in messages 
                if not (isinstance(msg, HumanMessage) and msg.name)
            ]
            
            has_ai_message = any(isinstance(msg, AIMessage) for msg in filtered_messages)
            if not has_ai_message:
                logger.info("后处理节点: 消息列表中没有 AI 回复，跳过保存")
            else:
                with get_db_context() as db:
                    chat_repo.save_conversation_from_messages(db, user_id, thread_id, filtered_messages)
                logger.info(
                    "多智能体对话已保存: thread_id=%s, user_id=%s, messages_count=%d", 
                    thread_id, user_id, len(messages)
                )
        except Exception as e:
            logger.error("多智能体后处理-保存失败: %s", e, exc_info=True)
        
        # 清理 DataFrame 缓存
        if thread_id:
            try:
                from app.ai.tools.chatTools import cleanup_thread_dataframes
                cleanup_thread_dataframes(thread_id)
                logger.debug("多智能体后处理: DataFrame 缓存已清理")
            except Exception as e:
                logger.warning("多智能体后处理-清理缓存失败: %s", e)
        
        return {}

    # 6. 定义评估节点（判断专家工作是否完成）
    def _evaluate_expert_work(state: MultiAgentState) -> dict:
        """评估专家工作节点：判断是否需要继续委派其他专家。
        
        判断逻辑：
        1. 检查是否达到最大迭代次数（3次）
        2. 检查最后一条消息是否是 AI 回复（无 tool_calls）
        3. 如果任务完成或达到迭代限制，返回 'complete'
        4. 否则返回 'continue'，让 Supervisor 重新评估
        """
        messages = state.get("messages", [])
        iteration_count = state.get("iteration_count") or 0
        
        # 防止无限循环：最多 3 轮迭代
        MAX_ITERATIONS = 3
        if iteration_count >= MAX_ITERATIONS:
            logger.warning(
                "评估节点: 达到最大迭代次数 (%d)，结束任务",
                MAX_ITERATIONS
            )
            return {"evaluation": "complete"}
        
        # 检查最后一条消息
        if not messages:
            return {"evaluation": "complete"}
        
        last_msg = messages[-1]
        
        # 如果最后一条是 AI 消息且没有 tool_calls，认为任务完成
        has_tool_calls = hasattr(last_msg, 'tool_calls') and last_msg.tool_calls
        
        if last_msg.type == "ai" and not has_tool_calls:
            logger.info("评估节点: 专家已完成任务，结束流程")
            return {"evaluation": "complete"}
        
        # 否则可能需要继续处理（由 Supervisor 重新评估）
        logger.info("评估节点: 任务可能需要继续，返回 Supervisor")
        
        # 🆕 发送协调状态给前端
        writer = get_stream_writer()
        emit_status(writer, message="专家工作需要继续，正在协调其他专家...", node="evaluate")
        
        return {
            "evaluation": "continue",
            "iteration_count": iteration_count + 1
        }
    
    # 7. 条件路由函数
    def should_continue_routing(state: MultiAgentState) -> Literal["postprocess", "supervisor"]:
        """根据评估结果决定下一步:
        - complete: 流向 postprocess 结束
        - continue: 返回 supervisor 重新评估
        """
        evaluation = state.get("evaluation", "complete")
        if evaluation == "continue":
            return "supervisor"
        return "postprocess"

    # 8. 构建 StateGraph（简化架构：移除 knowledge_expert）
    workflow = StateGraph(MultiAgentState)

    # 添加节点
    workflow.add_node("preprocess", _preprocess_multimodal)
    # 修复: Supervisor 也需要流式包装器,确保 LLM 输出是流式的
    workflow.add_node("supervisor", _create_streaming_agent_wrapper(supervisor_agent, "supervisor"))
    workflow.add_node("data_expert", _create_streaming_agent_wrapper(data_agent, "data_expert"))
    workflow.add_node("todo_expert", _create_streaming_agent_wrapper(todo_graph_app, "todo_expert"))
    workflow.add_node("evaluate", _evaluate_expert_work)
    workflow.add_node("postprocess", _postprocess)

    # Phase 2: 意图识别节点（借鉴 Flock + OpenAI Agents SDK routing）
    async def _classify_intent(state: MultiAgentState) -> dict:
        """意图识别节点：使用轻量级模型快速分类用户意图。"""
        from app.ai.intent_classifier import classify_intent
        
        messages = state.get("messages", [])
        if not messages:
            return {"detected_intent": "unknown", "intent_route": "supervisor"}
        
        last_msg = messages[-1]
        content = str(getattr(last_msg, "content", ""))
        
        # 跳过空消息或内部消息
        if not content or getattr(last_msg, "name", None) == "supervisor_handoff":
            return {"detected_intent": "unknown", "intent_route": "supervisor"}
        
        model_id = state.get("model_id")
        result = await classify_intent(content, model_id)
        
        # 🆕 发送意图识别状态
        writer = get_stream_writer()
        emit_status(writer, message=f"意图识别: {result.intent}", node="intent_classify")
        
        return {
            "detected_intent": result.intent,
            "intent_route": result.route_to
        }
    
    # 意图路由函数
    def route_by_intent(state: MultiAgentState) -> str:
        """根据意图识别结果路由到对应节点。"""
        route = state.get("intent_route", "supervisor")
        intent = state.get("detected_intent", "unknown")
        
        # 高置信度直接路由
        if route == "data_expert" and intent == "data_analysis":
            logger.info("意图路由: 直接到 data_expert")
            return "data_expert"
        elif route == "todo_expert" and intent == "todo_management":
            logger.info("意图路由: 直接到 todo_expert")
            return "todo_expert"
        
        # 其他情况走 Supervisor
        logger.info("意图路由: 到 supervisor (intent=%s)", intent)
        return "supervisor"
    
    # 🔧 修复问题5：移除 intent_classify 节点，简化架构
    # Supervisor 已经有 Prompt 指导路由，无需额外的意图分类
    
    # 添加边
    workflow.add_edge(START, "preprocess")
    workflow.add_edge("preprocess", "supervisor")
    
    # 专家执行完 -> 评估节点
    # 🔧 关键修复：添加专家到评估节点的边
    workflow.add_edge("data_expert", "evaluate")
    workflow.add_edge("todo_expert", "evaluate")
    
    # Supervisor 条件路由：检查 pending_handoff 或工具调用
    def supervisor_should_continue(state: MultiAgentState) -> str:
        """判断 Supervisor 下一步路由。
        
        路由逻辑：
        1. 如果有 pending_handoff → 路由到对应专家 (data_expert / todo_expert)
        2. 如果有其他 tool_calls → 路由到 evaluate
        3. 否则 → 路由到 postprocess
        """
        # 优先检查 pending_handoff（由 handoff 工具设置）
        pending_handoff = state.get("pending_handoff")
        if pending_handoff:
            target_agent = pending_handoff.get("target_agent")
            logger.info(f"Supervisor 检测到 pending_handoff，路由到 {target_agent}")
            
            if target_agent == AgentType.DATA:
                return "data_expert"
            elif target_agent == AgentType.TODO:
                return "todo_expert"
            else:
                logger.warning(f"未知的 target_agent: {target_agent}")
                return "postprocess"
        
        # 检查是否有其他工具调用
        messages = state.get("messages", [])
        if not messages:
            return "postprocess"
        
        last_msg = messages[-1]
        has_tool_calls = hasattr(last_msg, 'tool_calls') and last_msg.tool_calls
        
        if has_tool_calls:
            logger.debug("Supervisor 有工具调用，路由到 evaluate")
            return "evaluate"
        else:
            logger.debug("Supervisor 直接回复，路由到 postprocess")
            return "postprocess"
    
    workflow.add_conditional_edges(
        "supervisor",
        supervisor_should_continue,
        {
            "data_expert": "data_expert",
            "todo_expert": "todo_expert",
            "evaluate": "evaluate",
            "postprocess": "postprocess"
        }
    )
    
    # 评估节点 -> 条件路由
    workflow.add_conditional_edges(
        "evaluate",
        should_continue_routing,
        {
            "postprocess": "postprocess",  # 任务完成
            "supervisor": "supervisor",    # 返回 Supervisor 重新评估
        }
    )
    
    # Postprocess -> END
    workflow.add_edge("postprocess", END)

    # 6. 设置 Checkpointer
    if checkpointer is None:
        checkpointer = await get_checkpointer()
    
    # 7. 编译
    graph = workflow.compile(checkpointer=checkpointer)
    
    logger.info(
        "多智能体图编译完成（Manual Graph + Custom Handoff，启用思考: %s，模型: %s）", 
        enable_thinking, 
        model_id or "默认"
    )
    
    return graph


# 全局多智能体图缓存（线程安全）
_MULTI_AGENT_GRAPH_CACHE: Dict[Tuple[bool, Optional[str]], Any] = {}
_CACHE_LOCKS: Dict[Tuple[bool, Optional[str]], asyncio.Lock] = {}


async def get_multi_agent_graph(enable_thinking: bool = False, model_id: str = None):
    """获取全局多智能体图实例（缓存），线程安全。
    
    Args:
        enable_thinking: 是否启用深度思考模式
        model_id: 模型标识
        
    Returns:
        编译后的多智能体图实例
    """
    cache_key = (enable_thinking, model_id)
    
    # 获取或创建锁（防止并发创建）
    if cache_key not in _CACHE_LOCKS:
        _CACHE_LOCKS[cache_key] = asyncio.Lock()
    
    # 使用锁保护缓存访问
    async with _CACHE_LOCKS[cache_key]:
        if cache_key not in _MULTI_AGENT_GRAPH_CACHE:
            logger.info(
                "创建新的多智能体图实例: enable_thinking=%s, model_id=%s", 
                enable_thinking, model_id
            )
            _MULTI_AGENT_GRAPH_CACHE[cache_key] = await create_multi_agent_graph(
                enable_thinking=enable_thinking, 
                model_id=model_id
            )
    
    return _MULTI_AGENT_GRAPH_CACHE[cache_key]

