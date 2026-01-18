"""
待办Agent复杂多轮对话压力测试脚本.

测试目标:
验证 State 保持、澄清追问、任务拆解、冲突检测、优先级调整等能力。
"""
import asyncio
import logging
import sys
import os

# 添加项目根目录到 python path
sys.path.append(os.getcwd())

from langchain_core.messages import HumanMessage
from app.ai.workflow.todo_graph import create_todo_graph


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_test():
    print("🚀 开始复杂多轮对话压力测试...")
    
    # 初始化 Agent
    graph = create_todo_graph()
    
    # 配置
    config = {"configurable": {"thread_id": "test_thread_complex_001", "user_id": 1}}
    
    # 测试用例 (Round 1 - 10)
    test_cases = [
        {
            "round": 1,
            "input": "最近事情太多了，帮我把接下来要做的事情理一理。",
            "expect": "澄清追问 (clarify)",
            "desc": "模糊起始需求"
        },
        {
            "round": 2,
            "input": "工作的为主吧。\n大概有几个项目：\n* 一个是预售资金系统的投标材料\n* 一个是 AI 中台相关的方案\n* 还有几个零碎的临时事",
            "expect": "识别多项目",
            "desc": "高层级输入"
        },
        {
            "round": 3,
            "input": "预售资金那个挺急的，好像这周内要给。\nAI 中台倒是不那么急，但领导下周可能要听汇报。\n零碎的先不管。",
            "expect": "时间解析 + 优先级标记",
            "desc": "信息不完整 + 约束"
        },
        # Round 4 需要 Agent 先追问, 这里假设 Agent 已经追问了 (模拟用户回答)
        # 实际运行中看 Agent 是否真的追问了
        {
            "round": 4,
            "input": "技术方案我负责，但商务那块是公司部给。\n技术方案里要写系统架构、信创适配、实施计划。",
            "expect": "任务拆解 (decompose)",
            "desc": "任务拆解触发"
        },
        {
            "round": 5,
            "input": "对了，人力系统全行测评那件事之前说这周出初稿，可能要顺延一下。\n但办公室昨天又催了。",
            "expect": "冲突检测 (延期 vs 催办)",
            "desc": "插入历史任务 & 冲突"
        },
        {
            "round": 6,
            "input": "人力系统的放到下周二之前吧。\n但周一我基本一整天都在开会。",
            "expect": "时间冲突检测 (conflict)",
            "desc": "时间冲突显性化"
        },
        {
            "round": 7,
            "input": "AI 中台那个，其实不是写方案那么简单。\n我想先理一个落地路线图，顺便把组织模式也想一想。",
            "expect": "任务升级/复合任务",
            "desc": "任务深化 + 角色切换"
        },
        {
            "round": 8,
            "input": "等等，刚刚领导发消息了，说明天下午要一个\n“AI + 金融场景落地”的 1 页简要说明。",
            "expect": "紧急插单 (priority_adjust)",
            "desc": "临时插单"
        },
        {
            "round": 9,
            "input": "那 AI 中台的完整路线图可以先不做那么细，\n跟明天那个 1 页说明能不能合并一部分？",
            "expect": "任务合并 (merge)",
            "desc": "取消/合并决策"
        },
        {
            "round": 10,
            "input": "可以，按优先级给我。",
            "expect": "最终结构化输出",
            "desc": "最终确认"
        }
    ]
    
    # 模拟对话循环
    for i, case in enumerate(test_cases):
        print(f"\n\n================ Round {case['round']}: {case['desc']} ================")
        print(f"👤 用户: {case['input']}")
        print(f"🎯 预期: {case['expect']}")
        print("-" * 50)
        
        # 运行 Agent
        inputs = {"messages": [HumanMessage(content=case['input'])]}
        
        # 流式处理
        last_message = ""
        events = graph.stream(inputs, config, stream_mode="values")
        
        final_state = None
        for event in events:
            final_state = event
            if "messages" in event:
                last_msg = event["messages"][-1]
                if isinstance(last_msg, HumanMessage):
                    continue
                last_message = last_msg.content
                # print(f"🤖 Agent ({type(last_msg).__name__}): {last_msg.content}")
        
        print(f"🤖 Agent: {last_message}")
        
        # 打印关键状态 (如果有)
        if final_state:
            if "pending_clarifications" in final_state and final_state["pending_clarifications"]:
                 print(f"📝 待澄清: {final_state['pending_clarifications']}")
            if "detected_conflicts" in final_state and final_state["detected_conflicts"]:
                 print(f"⚠️ 冲突: {final_state['detected_conflicts']}")
            if "draft_todos" in final_state:
                todos = final_state.get("draft_todos", [])
                titles = [t.get('title') for t in todos]
                print(f"📋 草稿池 ({len(todos)}): {titles}")
        
        # 如果遇到 interrupt (confirm 节点), 需要恢复执行
        snapshot = graph.get_state(config)
        if snapshot.next:
            print(f"⏸️ 暂停 (Interrupt): {snapshot.next}")
            # 对于测试, 简单地继续 (某些场景可能需要模拟 confirm)
            # 但此测试主要观察交互, 除非必须 confirm 才能继续
            # 大部分 scenario 都在 clarify/analyze 阶段, 除了最后的 execute
            
            # 如果是 confirm 节点, 我们模拟用户确认
            # 注意: 这里的 confirm 节点不是 interrupt, interrupt 是在 execute 之前
            # graph 里的 interrupt_before=["execute"]
            
            if "execute" in snapshot.next:
                 print("⏩ 自动确认并继续执行...")
                 # state update to confirm? 
                 # 实际上 request_confirmation 节点已经运行了, 正在等待 execute
                 # 我们只需要发送 None 来继续 (或者带上 user_confirmed=True)
                 graph.update_state(config, {"user_confirmed": True})
                 for event in graph.stream(None, config, stream_mode="values"):
                     if "messages" in event:
                        print(f"🤖 Agent (After Confirm): {event['messages'][-1].content}")

if __name__ == "__main__":
    asyncio.run(run_test())
