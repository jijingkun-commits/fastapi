"""待办 Agent 复杂多轮对话压力测试 - Python 版（中文注释）。

直接通过 LangGraph Agent 进行测试，无需前端界面。

测试场景：城商行科技部开发中心经理的真实工作场景。
验证能力：
1. 多轮信息收集与状态保持
2. 时间解析（自然语言 + 相对时间）
3. 任务拆解 / 合并 / 依赖关系识别
4. 优先级动态调整
5. 冲突检测与澄清追问
6. 跨项目上下文切换
7. 变更管理（修改、取消、延后）
8. 隐含约束推理
9. 结构化输出
"""
import sys
from pathlib import Path
import json
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from langchain_core.messages import HumanMessage, AIMessage


def print_divider(char="=", length=60):
    """打印分隔线。"""
    print(char * length)


def print_round(round_num: int, title: str):
    """打印轮次标题。"""
    print(f"\n{'─' * 60}")
    print(f"📍 Round {round_num}: {title}")
    print(f"{'─' * 60}")


def check_keywords(response: str, keywords: list) -> bool:
    """检查响应是否包含任一关键词。"""
    return any(kw in response for kw in keywords)


def run_stress_test():
    """运行复杂多轮对话压力测试。"""
    print("\n" + "=" * 60)
    print("🧪 待办 Agent 复杂多轮对话压力测试")
    print("=" * 60)
    print(f"\n📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("👤 测试背景: 城商行科技部开发中心经理，多项目管理场景")
    print("=" * 60)
    
    try:
        from app.ai.workflow.todo_graph import create_todo_graph
        from langgraph.checkpoint.memory import MemorySaver
    except ImportError as e:
        print(f"\n❌ 导入失败: {e}")
        print("请确保在项目根目录下运行此脚本")
        return
    
    # 创建 Agent 图
    print("\n初始化待办 Agent...")
    graph = create_todo_graph()
    print("✅ Agent 创建成功")
    
    # 使用内存检查点保持状态
    memory = MemorySaver()
    
    # 定义对话轮次
    rounds = [
        {
            "round": 1,
            "title": "模糊起始需求",
            "user_message": "最近事情太多了，帮我把接下来要做的事情理一理。",
            "expected_keywords": ["哪些", "时间", "工作", "项目", "任务", "具体", "范围", "告诉"],
            "expected_behavior": "进入需求澄清模式，主动询问"
        },
        {
            "round": 2,
            "title": "高层级、非结构化输入",
            "user_message": """工作的为主吧。
大概有几个项目：
- 一个是预售资金系统的投标材料
- 一个是 AI 中台相关的方案
- 还有几个零碎的临时事""",
            "expected_keywords": ["预售资金", "AI中台", "AI 中台", "项目", "先聊", "详细"],
            "expected_behavior": "识别多项目，逐项追问"
        },
        {
            "round": 3,
            "title": "信息不完整 + 临时约束",
            "user_message": """预售资金那个挺急的，好像这周内要给。
AI 中台倒是不那么急，但领导下周可能要听汇报。
零碎的先不管。""",
            "expected_keywords": ["这周", "下周", "紧急", "优先", "汇报", "截止", "时间"],
            "expected_behavior": "识别相对时间，区分紧急程度"
        },
        {
            "round": 4,
            "title": "任务拆解触发",
            "user_message": """技术方案我负责，但商务那块是公司部给。
技术方案里要写系统架构、信创适配、实施计划。""",
            "expected_keywords": ["系统架构", "信创", "实施计划", "子任务", "拆解", "商务", "依赖"],
            "expected_behavior": "自动拆解任务，识别依赖"
        },
        {
            "round": 5,
            "title": "历史任务 + 冲突风险",
            "user_message": """对了，人力系统全行测评那件事之前说这周出初稿，可能要顺延一下。
但办公室昨天又催了。""",
            "expected_keywords": ["延期", "冲突", "催", "优先级", "调整", "人力系统", "测评"],
            "expected_behavior": "识别延期与催办冲突"
        },
        {
            "round": 6,
            "title": "时间冲突显性化",
            "user_message": """人力系统的放到下周二之前吧。
但周一我基本一整天都在开会。""",
            "expected_keywords": ["下周二", "周一", "会议", "时间", "冲突", "开会", "安排"],
            "expected_behavior": "解析时间约束，识别有效工作窗口"
        },
        {
            "round": 7,
            "title": "任务升级为复合任务",
            "user_message": """AI 中台那个，其实不是写方案那么简单。
我想先理一个落地路线图，顺便把组织模式也想一想。""",
            "expected_keywords": ["路线图", "组织", "阶段", "拆分", "AI中台", "复杂", "规划"],
            "expected_behavior": "升级为复合任务，自动拆分"
        },
        {
            "round": 8,
            "title": "临时紧急插单",
            "user_message": """等等，刚刚领导发消息了，说明天下午要一个
"AI + 金融场景落地"的 1 页简要说明。""",
            "expected_keywords": ["紧急", "高优先级", "明天", "领导", "1页", "简要", "优先"],
            "expected_behavior": "识别紧急任务，自动调整优先级"
        },
        {
            "round": 9,
            "title": "任务合并请求",
            "user_message": """那 AI 中台的完整路线图可以先不做那么细，
跟明天那个 1 页说明能不能合并一部分？""",
            "expected_keywords": ["合并", "结合", "复用", "路线图", "说明", "调整", "简化"],
            "expected_behavior": "支持任务合并，调整范围"
        },
        {
            "round": 10,
            "title": "最终汇总输出",
            "user_message": "可以，按优先级给我。",
            "expected_keywords": ["高优先级", "中优先级", "低优先级", "清单", "待办", "本周", "下周", "AI", "预售", "人力"],
            "expected_behavior": "生成结构化待办清单"
        }
    ]
    
    # 累积消息历史
    messages = []
    results = []
    
    # 配置（模拟用户ID和线程ID）
    config = {
        "configurable": {
            "thread_id": "stress_test_001",
            "user_id": 1
        }
    }
    
    for round_data in rounds:
        print_round(round_data["round"], round_data["title"])
        print(f"👤 用户: {round_data['user_message'][:80]}...")
        
        # 添加用户消息
        messages.append(HumanMessage(content=round_data["user_message"]))
        
        # 构建状态
        state = {
            "messages": messages,
            "user_id": 1,
            "thread_id": "stress_test_001",
            "pending_operation": None,
            "user_confirmed": None,
            "quick_mode": False,
            "conversation_context": None,
            "active_projects": None,
            "current_focus": None,
            "draft_todos": None,
            "pending_clarifications": None,
            "detected_conflicts": None,
            "time_constraints": None,
            "extracted_info": None,
            "project_queue": None,
            "current_project_index": None
        }
        
        try:
            # 运行 Agent
            result = graph.invoke(state, config)
            
            # 获取 AI 响应
            ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
            if ai_messages:
                response = ai_messages[-1].content
                messages.append(ai_messages[-1])  # 保持对话历史
            else:
                response = "(无响应)"
            
            # 检查关键词
            passed = check_keywords(response, round_data["expected_keywords"])
            
            # 记录结果
            result_entry = {
                "round": round_data["round"],
                "title": round_data["title"],
                "passed": passed,
                "response_preview": response[:200] if len(response) > 200 else response
            }
            results.append(result_entry)
            
            # 打印结果
            status = "✅ 通过" if passed else "❌ 未通过"
            print(f"\n🤖 AI: {response[:300]}{'...' if len(response) > 300 else ''}")
            print(f"\n期望行为: {round_data['expected_behavior']}")
            print(f"检查关键词: {round_data['expected_keywords'][:5]}...")
            print(f"测试结果: {status}")
            
        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "round": round_data["round"],
                "title": round_data["title"],
                "passed": False,
                "error": str(e)
            })
    
    # 打印测试总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    passed_count = sum(1 for r in results if r.get("passed", False))
    total_count = len(results)
    
    for r in results:
        status = "✅" if r.get("passed", False) else "❌"
        print(f"  {status} Round {r['round']}: {r['title']}")
    
    print(f"\n总计: {passed_count}/{total_count} 轮测试通过")
    print(f"通过率: {passed_count/total_count*100:.1f}%")
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过！待办 Agent 具备完整的多轮对话能力。")
    elif passed_count >= total_count * 0.7:
        print("\n⚠️  大部分测试通过，部分高级功能可能需要优化。")
    else:
        print("\n❌ 测试未达标，需要检查 Agent 实现。")
    
    return results


def run_single_capability_test(capability_name: str, test_message: str, expected_keywords: list):
    """运行单项能力测试。"""
    print(f"\n🧪 测试: {capability_name}")
    print(f"输入: {test_message}")
    
    try:
        from app.ai.workflow.todo_graph import create_todo_graph
        
        graph = create_todo_graph()
        
        state = {
            "messages": [HumanMessage(content=test_message)],
            "user_id": 1,
            "thread_id": f"test_{capability_name}",
            "pending_operation": None,
            "user_confirmed": None,
            "quick_mode": False,
            "conversation_context": None,
            "active_projects": None,
            "current_focus": None,
            "draft_todos": None,
            "pending_clarifications": None,
            "detected_conflicts": None,
            "time_constraints": None,
            "extracted_info": None,
            "project_queue": None,
            "current_project_index": None
        }
        
        result = graph.invoke(state)
        
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        if ai_messages:
            response = ai_messages[-1].content
        else:
            response = "(无响应)"
        
        passed = check_keywords(response, expected_keywords)
        status = "✅ 通过" if passed else "❌ 未通过"
        
        print(f"响应: {response[:300]}...")
        print(f"结果: {status}")
        
        return passed
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def run_analyze_intent_test():
    """直接测试意图分析功能（不依赖完整图）。"""
    print("\n" + "=" * 60)
    print("🧪 意图分析能力测试（核心逻辑验证）")
    print("=" * 60)
    
    try:
        # 只导入意图分析相关的模块
        from app.ai.llm_util import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
        import json
    except ImportError as e:
        print(f"\n❌ 导入失败: {e}")
        return
    
    # 意图分析提示词（简化版）
    ANALYZE_PROMPT = """你是待办管理助手的意图分析模块。

## 任务
分析用户消息,判断意图并提取信息。

## 意图分类
- clarify: 需要澄清（模糊/缺信息）
- query: 查询待办
- create: 创建待办
- update: 更新待办
- complete: 完成待办
- delete: 删除待办
- batch_create: 批量创建
- merge: 合并任务
- priority_adjust: 优先级调整
- context_switch: 上下文切换
- confirm: 用户确认
- constraint: 约束声明
- summarize: 汇总请求
- chat: 闲聊

## 输出格式
返回JSON:
```json
{
  "intent": "clarify",
  "needs_confirmation": false,
  "extracted_info": {},
  "is_complex": false,
  "missing_info": [],
  "projects": []
}
```

只返回JSON,不要其他内容。
"""
    
    # 测试用例
    test_cases = [
        {
            "name": "Round 1: 模糊起始",
            "message": "最近事情太多了，帮我把接下来要做的事情理一理。",
            "expected_intent": "clarify",
            "description": "应识别为需要澄清的模糊请求"
        },
        {
            "name": "Round 2: 多项目识别",
            "message": """工作的为主。有几个项目：
- 一个是预售资金系统
- 一个是 AI 中台
- 还有零碎的事""",
            "expected_intent": "clarify",
            "description": "应识别多个项目并准备逐项追问"
        },
        {
            "name": "Round 3: 时间解析",
            "message": "预售资金那个挺急的，好像这周内要给。AI 中台不急，领导下周听汇报。",
            "expected_intent": "clarify",
            "description": "应识别相对时间和紧急程度"
        },
        {
            "name": "Round 4: 任务拆解",
            "message": "技术方案里要写系统架构、信创适配、实施计划。",
            "expected_intent": "create",
            "description": "应识别为复杂任务需要拆解"
        },
        {
            "name": "Round 5: 冲突检测",
            "message": "人力系统测评之前说这周出初稿，可能要顺延。但办公室又催了。",
            "expected_intent": "update",
            "description": "应识别延期与催办的冲突"
        },
        {
            "name": "Round 6: 时间约束",
            "message": "人力系统的放到下周二之前吧。但周一我全天开会。",
            "expected_intent": "update",
            "description": "应识别时间约束（周一不可用）"
        },
        {
            "name": "Round 8: 紧急插单",
            "message": "刚刚领导发消息了，说明天下午要一个 AI+金融场景落地的1页说明。",
            "expected_intent": "create",
            "description": "应识别为紧急高优先级任务"
        },
        {
            "name": "Round 9: 任务合并",
            "message": "AI中台路线图跟那个1页说明能不能合并？",
            "expected_intent": "merge",
            "description": "应识别为合并请求"
        },
        {
            "name": "Round 10: 汇总输出",
            "message": "可以，按优先级给我。",
            "expected_intent": "summarize",
            "description": "应识别为汇总请求"
        }
    ]
    
    llm = get_llm()
    results = []
    
    for i, tc in enumerate(test_cases, 1):
        print(f"\n{'─' * 60}")
        print(f"📍 测试 {i}: {tc['name']}")
        print(f"{'─' * 60}")
        print(f"👤 输入: {tc['message'][:60]}...")
        print(f"📋 期望意图: {tc['expected_intent']}")
        
        try:
            messages = [
                SystemMessage(content=ANALYZE_PROMPT),
                HumanMessage(content=tc["message"])
            ]
            
            response = llm.invoke(messages, config={"tags": ["internal_thought"]})
            result_text = response.content
            
            # 解析 JSON
            analysis = json.loads(result_text)
            detected_intent = analysis.get("intent", "unknown")
            
            passed = detected_intent == tc["expected_intent"]
            status = "✅ 通过" if passed else "❌ 未通过"
            
            print(f"🤖 检测意图: {detected_intent}")
            print(f"📊 结果: {status}")
            
            if analysis.get("missing_info"):
                print(f"   缺失信息: {analysis['missing_info']}")
            if analysis.get("projects"):
                print(f"   识别项目: {analysis['projects']}")
            if analysis.get("is_complex"):
                print(f"   复杂任务: 是")
            
            results.append({
                "name": tc["name"],
                "passed": passed,
                "expected": tc["expected_intent"],
                "detected": detected_intent
            })
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            print(f"   原始响应: {result_text[:200]}")
            results.append({"name": tc["name"], "passed": False, "error": "JSON parse error"})
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            results.append({"name": tc["name"], "passed": False, "error": str(e)})
    
    # 测试总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    passed_count = sum(1 for r in results if r.get("passed", False))
    total_count = len(results)
    
    for r in results:
        status = "✅" if r.get("passed", False) else "❌"
        extra = ""
        if not r.get("passed") and r.get("detected"):
            extra = f" (检测到: {r['detected']})"
        print(f"  {status} {r['name']}{extra}")
    
    print(f"\n总计: {passed_count}/{total_count} 项测试通过")
    print(f"通过率: {passed_count/total_count*100:.1f}%")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="待办 Agent 压力测试")
    parser.add_argument("--full", action="store_true", help="运行完整 10 轮压力测试（需要数据库）")
    parser.add_argument("--quick", action="store_true", help="运行快速单项测试（需要数据库）")
    parser.add_argument("--analyze", action="store_true", help="运行意图分析测试（无需数据库）")
    args = parser.parse_args()
    
    if args.full:
        run_stress_test()
    elif args.quick:
        # 快速测试关键能力
        tests = [
            ("时间解析", "后天下午3点开会", ["3点", "15", "会议", "待办", "创建"]),
            ("紧急任务", "刚刚老板说马上要一份报告", ["紧急", "高", "优先", "马上"]),
            ("多项目", "有两个项目要做：系统A和系统B", ["系统A", "系统B", "项目", "先"]),
        ]
        
        print("\n🧪 快速能力验证测试\n")
        for name, msg, keywords in tests:
            run_single_capability_test(name, msg, keywords)
            print()
    elif args.analyze:
        run_analyze_intent_test()
    else:
        print("使用方法:")
        print("  python test_todo_stress.py --analyze  # 意图分析测试（推荐，无需数据库）")
        print("  python test_todo_stress.py --full     # 完整压力测试（需要数据库）")
        print("  python test_todo_stress.py --quick    # 快速能力验证（需要数据库）")
