"""LangChain 1.2+ Agent 高级特性完整示例。

本文件演示了 LangChain 1.2+ 的最新 Agent API (`langchain.agents.create_agent`) 的所有高级特性：

1. **Middleware** - 拦截模型调用和工具调用
   - `before_model` - 模型调用前钩子（动态 Prompt 注入）
   - `after_model` - 模型调用后钩子
   - `wrap_tool_call` - 工具调用拦截器 (异步)

2. **Dynamic System Prompt** - 根据用户输入动态修改系统提示词（技能注入）

3. **Artifact** - 使用 ToolMessage.artifact 隔离结构化数据

4. **Streaming** - 使用 astream_events 获取细粒度事件

5. **Checkpointer** - 会话状态持久化

运行方式：
    python -m app.ai.examples.advanced_agent_demo

注意：需要配置好 .env 文件中的 LLM API Key。
"""
import asyncio
import json
import logging
import re
from typing import Optional, Any, Annotated

from langchain.agents import create_agent
from langchain.agents.middleware import (
    before_model, 
    after_model, 
    wrap_tool_call
)
from langchain_core.tools import tool
from langchain_core.messages import (
    BaseMessage, 
    SystemMessage, 
    HumanMessage, 
    AIMessage,
    ToolMessage
)
from langgraph.checkpoint.memory import MemorySaver

# 设置日志
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ========================================================================
# 1. 工具定义
# ========================================================================

@tool
def search(query: str) -> str:
    """使用搜索引擎查找信息。"""
    logger.info("🔍 执行搜索: %s", query)
    # 模拟搜索结果
    if "天气" in query:
        return "北京今天晴，28°C，空气质量良好。"
    elif "python" in query.lower():
        return "Python 是一门流行的编程语言，最新版本是 3.12。"
    else:
        return f"搜索结果：关于'{query}'的最新信息已找到。"

@tool
def python_exec(code: str) -> str:
    """执行 Python 代码并返回结果。

    Args:
        code: 需要执行的 Python 代码
    """
    logger.info("🐍 执行 Python 代码...")
    # 模拟代码执行
    try:
        # 安全起见，这里只是模拟
        if "print" in code:
            return "代码执行成功。\n输出: Hello, World!\n\n![生成的图表](http://example.com/chart.png)"
        return "代码执行成功，无输出。"
    except Exception as e:
        return f"执行错误: {e}"

@tool
def data_analysis(data_description: str) -> str:
    """对数据进行分析。

    Args:
        data_description: 数据描述或 DataFrame 变量名
    """
    # 模拟返回包含图片的分析结果
    return f"""
数据分析完成！

## 数据概览
- 样本数量: 1000
- 特征数量: 10
- 缺失值: 无

![分析图表](http://example.com/analysis_chart.png)

## 结论
数据分布正常，无明显异常。
"""

# ========================================================================
# 2. 模拟技能库（Claude Agent Skills 风格）
# ========================================================================

SKILLS = {
    "data_science_expert": {
        "name": "data_science_expert",
        "description": "数据科学家技能，擅长 pandas、matplotlib 分析与可视化",
        "content": """
## 你是一位资深数据科学家
1. 始终先用 df.head() 查看数据
2. 检查缺失值: df.isnull().sum()
3. 生成可视化图表时必须包含中文标题
"""
    },
    "python_expert": {
        "name": "python_expert",
        "description": "Python 编程专家，擅长算法和最佳实践",
        "content": """
## 你是一位 Python 编程专家
1. 遵循 PEP8 规范
2. 优先使用 f-string 格式化字符串
3. 复杂逻辑使用类型注解
"""
    }
}

def match_skill(query: str) -> Optional[dict]:
    """简单的技能匹配（生产环境建议使用向量检索）。"""
    query_lower = query.lower()
    if any(kw in query_lower for kw in ["数据", "分析", "pandas", "图表"]):
        return SKILLS["data_science_expert"]
    if any(kw in query_lower for kw in ["python", "代码", "编程", "算法"]):
        return SKILLS["python_expert"]
    return None

# ========================================================================
# 3. Middleware 定义
# ========================================================================

# 3.1 模型调用前钩子 - 动态注入技能
@before_model
def inject_skill_middleware(request, runtime):
    """在模型调用前，根据用户问题动态注入相关技能到 System Prompt。"""
    messages = request.messages
    
    # 获取用户最新的问题
    user_query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_query = msg.content
            break
    
    if not user_query:
        return request
    
    # 匹配技能
    skill = match_skill(user_query)
    if skill:
        logger.info("💡 注入技能: %s", skill["name"])
        # 获取原始 System Prompt
        original_system = ""
        for i, msg in enumerate(messages):
            if isinstance(msg, SystemMessage):
                original_system = msg.content
                # 注入技能指令
                enhanced_prompt = f"{original_system}\n\n## 当前激活技能\n{skill['content']}"
                messages[i] = SystemMessage(content=enhanced_prompt)
                break
    
    return request

# 3.2 模型调用后钩子 - 日志记录
@after_model
def log_model_output_middleware(request, response, runtime):
    """记录模型输出（用于调试和监控）。"""
    if response and hasattr(response, "content"):
        logger.info("🤖 模型输出长度: %d 字符", len(str(response.content)))
    return response

# 3.3 工具调用中间件 - 使用 Artifact 隔离图片 URL
@wrap_tool_call
async def image_artifact_middleware(request, execute):
    """拦截工具输出，将图片 URL 隔离到 artifact 中。
    
    这样 AI 只看到纯文本，不会在回复中重复图片链接。
    """
    result = await execute(request)
    
    if result and result.content:
        content = str(result.content)
        
        # 提取图片
        images = []
        for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', content):
            images.append({
                "alt": match.group(1) or "图片",
                "url": match.group(2)
            })
        
        if images:
            # 移除图片 Markdown
            text_only = re.sub(r'!\[[^\]]*\]\([^)]+\)', '[图片已生成]', content)
            logger.info("🖼️ 检测到 %d 张图片，已隔离到 artifact", len(images))
            
            # 返回新的 ToolMessage，带 artifact
            return ToolMessage(
                content=text_only,  # AI 只看到这个
                artifact={"images": images},  # 程序读取这个
                tool_call_id=result.tool_call_id
            )
    
    return result

# ========================================================================
# 4. 创建 Agent
# ========================================================================

def create_advanced_agent(model=None, checkpointer=None):
    """创建一个包含所有高级特性的 Agent。
    
    Args:
        model: LLM 实例，默认使用 DeepSeek
        checkpointer: 可选的 Checkpointer 实例
    
    Returns:
        编译后的 Agent 图
    """
    from app.ai.llm_util import get_llm
    
    if model is None:
        model = get_llm()
    
    if checkpointer is None:
        checkpointer = MemorySaver()
    
    # 工具列表
    tools = [search, python_exec, data_analysis]
    
    # 系统提示词
    system_prompt = """你是一个专业的 AI 助手。

## 核心能力
1. 搜索互联网获取最新信息
2. 执行 Python 代码进行数据分析
3. 根据用户需求调用合适的工具

## 回复规范
- 使用中文回复
- 先思考再行动
- 如果不确定，请坦诚说明
"""
    
    # 创建 Agent
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        middleware=[
            inject_skill_middleware,      # 动态技能注入
            log_model_output_middleware,  # 日志记录
            image_artifact_middleware,    # 图片隔离
        ],
    )
    
    logger.info("✅ Agent 创建完成，使用 %d 个中间件", 3)
    return agent


# ========================================================================
# 5. 运行演示
# ========================================================================

async def demo():
    """演示 Agent 运行。"""
    print("\n" + "="*60)
    print("🚀 LangChain 1.2+ 高级 Agent 演示")
    print("="*60 + "\n")
    
    # 创建 Agent
    agent = create_advanced_agent()
    
    # 测试用例
    test_queries = [
        "帮我分析一下这个数据集的缺失值情况",  # 触发 data_science_expert 技能
        "写一段 Python 代码打印 Hello World",   # 触发 python_expert 技能 + 图片处理
    ]
    
    for query in test_queries:
        print(f"\n📝 用户: {query}\n")
        print("-" * 40)
        
        # 使用 astream_events 获取细粒度事件
        async for event in agent.astream_events(
            {"messages": [HumanMessage(content=query)]},
            version="v2",
        ):
            kind = event.get("event")
            
            if kind == "on_chat_model_stream":
                # 流式 Token
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    print(chunk.content, end="", flush=True)
                    
            elif kind == "on_tool_end":
                # 工具执行完成
                output = event.get("data", {}).get("output")
                if output and hasattr(output, "artifact") and output.artifact:
                    print(f"\n\n📎 [Artifact] 检测到隔离数据: {json.dumps(output.artifact, ensure_ascii=False)}")
        
        print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(demo())
