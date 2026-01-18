"""聊天 Agent 图定义模块（中文注释）。

本模块采用混合架构：
- 使用 StateGraph 保持图的灵活性和可扩展性
- 使用 create_agent 创建带系统提示词和中间件的 Agent 作为子图节点
- 可以在 Agent 节点前后添加自定义节点（如 preprocess、postprocess）

架构示意：
    START -> preprocess -> agent_subgraph -> postprocess -> END
"""
import logging
from typing import Annotated, Sequence, TypedDict, Optional, Literal


from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from app.ai.llm_util import get_llm
from app.ai.middleware import message_trim_middleware
from app.ai.prompts import CHAT_AGENT_SYSTEM_PROMPT
from app.db.postgres_checkpoint import get_checkpointer
from app.ai.utils.image_fixer import fix_missing_image_links


logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """Agent 状态定义。
    
    Attributes:
        messages: 对话消息列表，使用 add_messages 归约器自动追加
        thinking_content: Qwen Think 模式的思考过程内容
        user_id: 用户 ID（用于保存对话）
        thread_id: 对话线程 ID（用于保存对话）
        enable_thinking: 是否启用深度思考模式
        model_id: 模型标识（用于动态选择模型）
        _graph_type: Graph 类型标记（用于 resume 时检测）
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    thinking_content: Optional[str]
    user_id: Optional[int]
    thread_id: Optional[str]
    enable_thinking: Optional[bool]
    model_id: Optional[str]
    # 显式标记 Graph 类型，用于 resume 时检测
    _graph_type: Optional[Literal["single_agent"]]
    # Multi-Agent 兼容字段
    attachment_analysis: Optional[str]
    evaluation: Optional[str]
    iteration_count: Optional[int]


def _get_tools():
    """获取可用的工具列表（包括本地工具和 MCP 工具）。"""
    tools = []
    
    # 加载本地工具
    try:
        from app.ai.tools.chatTools import search_tool, sql_inter, python_inter, fig_inter
        if search_tool:
            tools.append(search_tool)
        tools.extend([sql_inter, python_inter, fig_inter])
        logger.info("已加载 %d 个本地工具", len(tools))
    except ImportError as e:
        logger.warning("本地工具加载失败: %s", e)
    except Exception as e:
        logger.error("本地工具初始化错误: %s", e)
    
    # 加载 RAGFlow 知识库检索工具（如果已配置）
    try:
        from app.ai.tools.ragflow_tool import knowledge_search, is_ragflow_configured
        if is_ragflow_configured():
            tools.append(knowledge_search)
            logger.info("已加载 RAGFlow 知识库检索工具")
        else:
            logger.debug("RAGFlow 未配置，跳过知识库工具")
    except ImportError as e:
        logger.debug("RAGFlow 工具未安装: %s", e)
    except Exception as e:
        logger.warning("RAGFlow 工具加载失败: %s", e)
    
    # 加载智谱 Vision 图片理解工具（如果已配置）
    try:
        from app.ai.tools.vision_tool import analyze_image, is_vision_configured
        if is_vision_configured():
            tools.append(analyze_image)
            logger.info("已加载 Vision 图片理解工具")
        else:
            logger.debug("Vision 模型未配置，跳过图片理解工具")
    except ImportError as e:
        logger.debug("Vision 工具未安装: %s", e)
    except Exception as e:
        logger.warning("Vision 工具加载失败: %s", e)
    
    # 加载文件读取工具（用于读取上传的 Excel、CSV 等文件）
    try:
        from app.ai.tools.file_tools import read_uploaded_file
        tools.append(read_uploaded_file)
        logger.info("已加载文件读取工具 (read_uploaded_file)")
    except ImportError as e:
        logger.debug("文件读取工具未安装: %s", e)
    except Exception as e:
        logger.warning("文件读取工具加载失败: %s", e)
    
    return tools


async def _get_tools_with_mcp():
    """获取所有工具（包括 MCP 工具，异步版本）。"""
    from app.core.config import MCP_CHART_ENABLED
    
    tools = _get_tools()
    
    # 加载 MCP 图表工具（如果启用）
    if MCP_CHART_ENABLED:
        try:
            from app.ai.mcp import load_chart_tools
            mcp_tools = await load_chart_tools()
            if mcp_tools:
                tools.extend(mcp_tools)
                logger.info("已加载 %d 个 MCP 图表工具", len(mcp_tools))
        except Exception as e:
            logger.warning("MCP 图表工具加载失败（服务可能未启动）: %s", e)
    
    return tools





async def _create_agent_subgraph(enable_thinking: bool = False, model_id: str = None):
    """创建 Agent 子图（使用 LangChain 1.2.0 的 create_agent + middleware）。
    
    使用 LangChain 1.2.0 官方的 create_agent API，支持：
    - system_prompt: 系统提示词
    - middleware: 中间件列表（装饰器风格）
    
    Args:
        enable_thinking: 是否启用深度思考模式
        model_id: 可选模型标识
    
    Returns:
        CompiledStateGraph: 编译后的 Agent
    """
    from langchain.agents import create_agent
    from langchain.agents.middleware import wrap_tool_call
    from langgraph.checkpoint.memory import InMemorySaver
    import re
    
    llm = get_llm(force_thinking=enable_thinking, model_id=model_id)
    
    # 使用异步函数加载工具（包括 MCP 工具）
    tools = await _get_tools_with_mcp()
    
    # 创建图片处理中间件：使用 Artifact 机制隔离 URL
    # 使用 create_agent 创建 Agent（langchain 1.2.0+ API）
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=CHAT_AGENT_SYSTEM_PROMPT,
        middleware=[],
    )
    
    logger.info("Agent 创建完成（create_agent + middleware），工具数量: %d，启用思考: %s，模型: %s", 
                len(tools), enable_thinking, model_id or "默认")
    return agent


def _preprocess(state: AgentState) -> dict:
    """预处理节点。
    
    在 Agent 执行前进行预处理：
    1. 验证消息序列，移除不完整的 tool_calls（关键！）
    2. 可扩展添加其他预处理逻辑
    """
    from app.ai.message_utils import validate_messages
    
    messages = state.get("messages", [])
    original_count = len(messages)
    
    # 验证消息序列（移除不完整的 tool_calls，且为 DeepSeek 修复 missing reasoning_content）
    # 判断是否为 DeepSeek 或启用思考模式
    enable_thinking = state.get("enable_thinking", False)
    model_id = state.get("model_id")
    
    is_deepseek = False
    if model_id:
        is_deepseek = "deepseek" in model_id.lower() or "reasoner" in model_id.lower()
    else:
        # 如果未指定 model_id，检查默认配置
        from app.ai.config import MODEL_TYPE, MODEL_NAME
        if "deepseek" in MODEL_NAME.lower() or "reasoner" in MODEL_NAME.lower():
             is_deepseek = True
        elif MODEL_TYPE == "deepseek":
             is_deepseek = True
    
    # 如果是 DeepSeek 或开启了 Thinking，尝试修复 reasoning_content
    should_fix = enable_thinking or is_deepseek
    
    validated = validate_messages(messages, fix_reasoning=should_fix)
    
    if len(validated) != original_count or should_fix:
        # should_fix 为 True 时，可能只是修改了字段内容，len 没变，但仍需更新 state
        logger.debug("预处理节点: 验证/修复完成, should_fix=%s, 消息数 %d -> %d", should_fix, original_count, len(validated))
        return {"messages": validated, "_graph_type": "single_agent"}
    
    logger.debug("预处理节点: 消息数量=%d, 无需修复", original_count)
    # 显式标记 Graph 类型，用于 resume 时检测
    return {"_graph_type": "single_agent"}


def _postprocess(state: AgentState) -> dict:
    """后处理节点：调试日志 + 自动保存对话到 MySQL + 清理临时数据。
    
    此节点在每次图执行完成后被调用，负责：
    1. 打印调试日志
    2. 自动保存对话到 MySQL（从 state 中提取 user_id、thread_id）
    3. 清理该轮对话产生的 DataFrame 缓存（防止内存泄漏）
    """
    messages = state.get("messages", [])
    
    # 橙色 ANSI 颜色代码
    ORANGE = "\033[38;5;208m"
    RESET = "\033[0m"
    
    # 原样打印所有消息（调试用）
    logger.info(f"{ORANGE}{'='*60}{RESET}")
    logger.info(f"{ORANGE}[消息列表] 共 {len(messages)} 条消息:{RESET}")
    for i, msg in enumerate(messages):
        logger.info(f"{ORANGE}  [{i}] {msg}{RESET}")
    logger.info(f"{ORANGE}{'='*60}{RESET}")
    
    # 自动保存对话到 数据库
    user_id = state.get("user_id")
    thread_id = state.get("thread_id")
    if thread_id and messages:
        try:
            from app.db.session import get_db_context
            from app.repositories import chat_repo
            
            with get_db_context() as db:
                # 修复可能缺失的图片链接（在保存前）
                # 即使 LLM 忘了生成图片的 Markdown 链接，只要工具生成了，就强制追加到最后
                fixed_messages = fix_missing_image_links(messages)
                chat_repo.save_conversation_from_messages(db, user_id, thread_id, fixed_messages)
        except Exception as e:
            logger.error("后处理节点-保存失败: %s", e)
    
    # 清理该轮对话产生的 DataFrame 缓存（一轮结束即清理，防止内存泄漏）
    if thread_id:
        try:
            from app.ai.tools.chatTools import cleanup_thread_dataframes
            if cleanup_thread_dataframes(thread_id):
                logger.debug("后处理节点: 已清理 thread_id=%s 的 DataFrame 缓存", thread_id)
        except Exception as e:
            logger.warning("后处理节点-清理 DataFrame 失败: %s", e)
    
    return {}


async def create_chat_graph(checkpointer=None, enable_thinking: bool = False, model_id: str = None):
    """创建聊天 StateGraph（混合架构）。
    
    使用 StateGraph 作为主图，将 Agent 作为子图节点嵌入。
    这样既能使用官方中间件，又能保持图的可扩展性。
    
    图结构：
        START -> preprocess -> agent -> postprocess -> END
    
    Args:
        checkpointer: 可选的 Checkpointer 实例
        enable_thinking: 是否启用深度思考模式
        model_id: 可选模型标识
        
    Returns:
        编译后的 CompiledGraph
    """
    # 创建 Agent 子图（根据 enable_thinking 和 model_id 配置 LLM）
    agent_subgraph = await _create_agent_subgraph(enable_thinking=enable_thinking, model_id=model_id)
    
    # 创建主图
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("preprocess", _preprocess)      # 预处理节点（可扩展）
    # 封装 Agent 节点以捕获异常，确保 postprocess 总是执行
    async def safe_agent_node(state, config):
        try:
            return await agent_subgraph.ainvoke(state, config)
        except Exception as e:
            # 关键:如果是 GraphInterrupt (中断信号)，必须抛出，否则无法触发人工确认!
            if type(e).__name__ == "GraphInterrupt":
                raise e
                
            logger.exception("Agent 节点执行异常: %s", e)
            # 返回错误消息，以便前端知道发生了错误，且 postprocess 能保存
            # 注意：需构造符合 state 结构的数据
            from langchain_core.messages import AIMessage
            error_msg = f"Sorry, the system encountered an internal error: {str(e)}"
            return {"messages": [AIMessage(content=error_msg)]}

    workflow.add_node("agent", safe_agent_node)        # 使用封装后的安全节点
    workflow.add_node("postprocess", _postprocess)    # 后处理节点（可扩展）
    
    # 设置边
    workflow.add_edge(START, "preprocess")
    workflow.add_edge("preprocess", "agent")
    workflow.add_edge("agent", "postprocess")
    workflow.add_edge("postprocess", END)
    
    # 设置 Checkpointer
    if checkpointer is None:
        checkpointer = await get_checkpointer()
    
    # 编译图
    graph = workflow.compile(checkpointer=checkpointer)
    logger.info("聊天 StateGraph 编译完成（混合架构，启用思考: %s，模型: %s）", enable_thinking, model_id or "默认")
    
    return graph


# 全局图实例缓存（key: (enable_thinking, model_id)）
_CHAT_GRAPH_CACHE: dict[tuple, any] = {}


async def get_chat_graph(enable_thinking: bool = False, model_id: str = None):
    """获取全局聊天图实例（根据 enable_thinking 和 model_id 缓存不同实例）。"""
    cache_key = (enable_thinking, model_id)
    if cache_key not in _CHAT_GRAPH_CACHE:
        _CHAT_GRAPH_CACHE[cache_key] = await create_chat_graph(enable_thinking=enable_thinking, model_id=model_id)
    return _CHAT_GRAPH_CACHE[cache_key]
