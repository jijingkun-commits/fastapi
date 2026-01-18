"""待办 Agent 浏览器模拟测试 - 通过 API 进行多轮对话测试（中文注释）。

直接调用后端 API 进行测试，模拟浏览器行为。
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

# 测试用户凭证（参见 .agent/docs/测试环境配置.md）
TEST_USER = {
    "username": "jjk",
    "password": ""
}


def print_divider(char="=", length=60):
    print(char * length)


def print_round(round_num: int, title: str):
    print(f"\n{'─' * 60}")
    print(f"📍 Round {round_num}: {title}")
    print(f"{'─' * 60}")


def login():
    """登录获取 token。"""
    print("🔐 正在登录...")
    try:
        resp = requests.post(
            f"{BASE_URL}/login",
            json={"username": TEST_USER["username"], "password": TEST_USER["password"]},
            headers={"Content-Type": "application/json"}
        )
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            print(f"✅ 登录成功")
            return token
        else:
            print(f"❌ 登录失败: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return None


def send_chat_message(token: str, message: str, conversation_id: str = None):
    """发送聊天消息。"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": message,
        "delay_ms": 30,
        "use_multi_agent": True,
    }
    
    if conversation_id:
        payload["thread_id"] = conversation_id
    
    try:
        resp = requests.post(
            f"{BASE_URL}/chat/stream",
            json=payload,
            headers=headers,
            stream=True,
            timeout=120
        )
        
        if resp.status_code != 200:
            print(f"❌ 请求失败: {resp.status_code} - {resp.text}")
            return None, None
        
        # 收集流式响应
        full_response = ""
        new_conversation_id = conversation_id
        current_event = None
        
        for line in resp.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                # 解析 SSE 格式: event: xxx 和 data: xxx
                if line_str.startswith("event: "):
                    current_event = line_str[7:]
                elif line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        
                        # 根据事件类型处理
                        if current_event == "init":
                            new_conversation_id = data.get("thread_id", conversation_id)
                        elif current_event == "token":
                            full_response += data.get("content", "")
                        elif current_event == "meta":
                            new_conversation_id = data.get("thread_id", new_conversation_id)
                        
                    except json.JSONDecodeError:
                        pass
        
        return full_response, new_conversation_id
        
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return None, None


def check_keywords(response: str, keywords: list) -> bool:
    """检查响应是否包含任一关键词。"""
    if not response:
        return False
    return any(kw in response for kw in keywords)


def query_todos(token: str):
    """查询当前待办列表。"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(f"{BASE_URL}/todos", headers=headers)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"⚠️ 查询待办失败: {resp.status_code}")
            return []
    except Exception as e:
        print(f"⚠️ 查询待办异常: {e}")
        return []


def run_stress_test():
    """运行多轮对话压力测试。"""
    print("\n" + "=" * 60)
    print("🧪 待办 Agent 多轮对话压力测试 (API 模式)")
    print("=" * 60)
    print(f"\n📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("👤 测试背景: 城商行科技部开发中心经理，多项目管理场景")
    print("=" * 60)
    
    # 登录
    token = login()
    if not token:
        print("\n❌ 无法登录，测试终止")
        return
    
    # 对话轮次
    rounds = [
        {
            "round": 1,
            "title": "模糊起始需求",
            "message": "最近事情太多了，帮我把接下来要做的事情理一理。",
            "expected_keywords": ["哪些", "时间", "工作", "项目", "任务", "具体", "范围", "告诉", "了解"],
            "expected_behavior": "进入需求澄清模式，主动询问"
        },
        {
            "round": 2,
            "title": "高层级、非结构化输入",
            "message": """工作的为主吧。
大概有几个项目：
- 一个是预售资金系统的投标材料
- 一个是 AI 中台相关的方案
- 还有几个零碎的临时事""",
            "expected_keywords": ["预售资金", "AI中台", "AI 中台", "项目", "先", "详细", "投标", "方案"],
            "expected_behavior": "识别多项目，逐项追问"
        },
        {
            "round": 3,
            "title": "信息不完整 + 临时约束",
            "message": """预售资金那个挺急的，好像这周内要给。
AI 中台倒是不那么急，但领导下周可能要听汇报。
零碎的先不管。""",
            "expected_keywords": ["这周", "下周", "紧急", "优先", "汇报", "截止", "时间", "急", "领导"],
            "expected_behavior": "识别相对时间，区分紧急程度"
        },
        {
            "round": 4,
            "title": "任务拆解触发",
            "message": """技术方案我负责，但商务那块是公司部给。
技术方案里要写系统架构、信创适配、实施计划。""",
            "expected_keywords": ["系统架构", "信创", "实施计划", "子任务", "拆解", "商务", "依赖", "技术方案"],
            "expected_behavior": "自动拆解任务，识别依赖"
        },
        {
            "round": 5,
            "title": "历史任务 + 冲突风险",
            "message": """对了，人力系统全行测评那件事之前说这周出初稿，可能要顺延一下。
但办公室昨天又催了。""",
            "expected_keywords": ["延期", "冲突", "催", "优先级", "调整", "人力系统", "测评", "顺延", "办公室"],
            "expected_behavior": "识别延期与催办冲突"
        },
        {
            "round": 6,
            "title": "时间冲突显性化",
            "message": """人力系统的放到下周二之前吧。
但周一我基本一整天都在开会。""",
            "expected_keywords": ["下周二", "周一", "会议", "时间", "冲突", "开会", "安排", "不可用"],
            "expected_behavior": "解析时间约束，识别有效工作窗口"
        },
        {
            "round": 7,
            "title": "任务升级为复合任务",
            "message": """AI 中台那个，其实不是写方案那么简单。
我想先理一个落地路线图，顺便把组织模式也想一想。""",
            "expected_keywords": ["路线图", "组织", "阶段", "拆分", "AI中台", "复杂", "规划", "落地"],
            "expected_behavior": "升级为复合任务，自动拆分"
        },
        {
            "round": 8,
            "title": "临时紧急插单",
            "message": """等等，刚刚领导发消息了，说明天下午要一个
"AI + 金融场景落地"的 1 页简要说明。""",
            "expected_keywords": ["紧急", "高优先级", "明天", "领导", "1页", "简要", "优先", "金融", "AI"],
            "expected_behavior": "识别紧急任务，自动调整优先级"
        },
        {
            "round": 9,
            "title": "任务合并请求",
            "message": """那 AI 中台的完整路线图可以先不做那么细，
跟明天那个 1 页说明能不能合并一部分？""",
            "expected_keywords": ["合并", "结合", "复用", "路线图", "说明", "调整", "简化", "部分"],
            "expected_behavior": "支持任务合并，调整范围"
        },
        {
            "round": 10,
            "title": "最终汇总输出",
            "message": "可以，按优先级给我。",
            "expected_keywords": ["高优先级", "中优先级", "低优先级", "清单", "待办", "本周", "下周", "AI", "预售", "人力", "🔴", "🟡", "🟢"],
            "expected_behavior": "生成结构化待办清单"
        }
    ]
    
    conversation_id = None
    results = []
    
    for round_data in rounds:
        print_round(round_data["round"], round_data["title"])
        print(f"👤 用户: {round_data['message'][:80]}...")
        
        # 发送消息
        response, conversation_id = send_chat_message(
            token, 
            round_data["message"], 
            conversation_id
        )
        
        if response:
            # 检查关键词
            passed = check_keywords(response, round_data["expected_keywords"])
            status = "✅ 通过" if passed else "⚠️ 部分匹配"
            
            # 打印响应（截取前300字符）
            print(f"\n🤖 AI: {response[:400]}{'...' if len(response) > 400 else ''}")
            print(f"\n期望行为: {round_data['expected_behavior']}")
            print(f"检查关键词: {round_data['expected_keywords'][:5]}...")
            print(f"测试结果: {status}")
            
            results.append({
                "round": round_data["round"],
                "title": round_data["title"],
                "passed": passed,
                "response_length": len(response)
            })
        else:
            print(f"\n❌ 无响应")
            results.append({
                "round": round_data["round"],
                "title": round_data["title"],
                "passed": False,
                "error": "no_response"
            })
        
        # 短暂等待，避免请求过快
        time.sleep(1)
    
    # 查询数据库中的待办
    print("\n" + "=" * 60)
    print("📊 数据库验证 - 待办列表")
    print("=" * 60)
    
    todos = query_todos(token)
    if todos:
        print(f"\n共有 {len(todos)} 个待办:\n")
        for todo in todos[:10]:
            priority_emoji = {1: "🔴", 2: "🟡", 3: "🟢"}.get(todo.get("priority"), "⚪")
            status_emoji = {"todo": "⬜", "in_progress": "◐", "done": "✅"}.get(todo.get("status"), "❓")
            print(f"  {priority_emoji} {status_emoji} [{todo.get('id')}] {todo.get('title')}")
            if todo.get("due_date"):
                print(f"      截止: {todo.get('due_date')[:10]}")
    else:
        print("\n⚠️ 数据库中暂无待办记录")
    
    # 测试总结
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


if __name__ == "__main__":
    run_stress_test()
