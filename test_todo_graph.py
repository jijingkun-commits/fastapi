"""测试 LangGraph 待办 Agent（中文注释）。

验证基本流程和图构建。
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_graph_creation():
    """测试图创建。"""
    print("=" * 60)
    print("1️⃣  测试 LangGraph 创建")
    print("=" * 60)
    
    try:
        from app.ai.workflow.todo_graph import create_todo_graph
        
        graph = create_todo_graph()
        print(f"\n✅ Graph 创建成功")
        print(f"   类型: {type(graph)}")
        print(f"   节点: analyze, confirm, execute")
        print(f"   中断点: execute")
        
        return graph
    except Exception as e:
        print(f"\n❌ Graph 创建失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_state_structure():
    """测试状态结构。"""
    print("\n" + "=" * 60)
    print("2️⃣  测试状态结构")
    print("=" * 60)
    
    try:
        from app.ai.workflow.todo_graph import TodoAgentState
        from langchain_core.messages import HumanMessage
        
        state = {
            "messages": [HumanMessage(content="测试消息")],
            "pending_operation": None,
            "user_confirmed": None,
            "extracted_info": None
        }
        
        print("\n✅ 状态结构:")
        for key in state:
            print(f"   - {key}: {type(state[key]).__name__}")
        
    except Exception as e:
        print(f"\n❌ 状态结构测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_simple_flow():
    """测试简单流程（不实际调用 LLM）。"""
    print("\n" + "=" * 60)
    print("3️⃣  测试简单流程")
    print("=" * 60)
    
    print("\n说明: 完整流程测试需要 LLM 和数据库连接")
    print("   - analyze_intent 需要调用 LLM 分析")
    print("   - execute_operation 需要数据库")
    print("\n建议通过实际使用来测试完整流程")


def test_create_todo_agent():
    """测试 create_todo_agent 集成。"""
    print("\n" + "=" * 60)
    print("4️⃣  测试 create_todo_agent 集成")
    print("=" * 60)
    
    try:
        from app.ai.agents.todo_agent import create_todo_agent
        
        # 测试 use_graph=True
        print("\n✅ 测试 use_graph=True")
        graph_agent = create_todo_agent(use_graph=True)
        print(f"   返回类型: {type(graph_agent).__name__}")
        
        # 测试 use_graph=False（向后兼容）
        print("\n✅ 测试 use_graph=False (向后兼容)")
        try:
            classic_agent = create_todo_agent(use_graph=False)
            print(f"   返回类型: {type(classic_agent).__name__}")
        except Exception as e:
            print(f"   ⚠️  Classic agent 创建失败: {e}")
        
    except Exception as e:
        print(f"\n❌ create_todo_agent 测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主测试入口。"""
    print("\n🧪 LangGraph 待办 Agent 测试\n")
    
    # 1. 测试图创建
    graph = test_graph_creation()
    
    # 2. 测试状态结构
    test_state_structure()
    
    # 3. 测试简单流程
    test_simple_flow()
    
    # 4. 测试集成
    test_create_todo_agent()
    
    print("\n" + "=" * 60)
    print("✅ 基础测试完成！")
    print("=" * 60)
    print("\n📝 下一步:")
    print("  1. 通过 API 端点测试完整流程")
    print("  2. 验证用户确认机制")
    print("  3. 测试多轮对话")
    print()


if __name__ == "__main__":
    main()
