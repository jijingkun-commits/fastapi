"""复合任务串行队列回归测试。"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.ai.contracts.delivery_contract_validators import validate_coverage_report_contract
from app.ai.state import AgentType
from app.ai.workflow.multi_agent_graph import (
    _build_delivery_artifacts,
    _build_multi_intent_summary_content,
    _compute_coverage_report,
    _evaluate_handoff_progress,
    _render_coverage_blocked_message,
    _render_final_answer,
    _resolve_coverage_gate_route,
)


def test_evaluate_handoff_progress_consumes_queue_before_complete() -> None:
    """有 handoff_queue 时必须继续执行下一个专家，而不是提前 complete。"""
    state = {
        "messages": [
            HumanMessage(content="嘉兴天气、网银功能、并创建待办"),
            AIMessage(content="天气已查询，准备继续处理。"),
        ],
        "pending_handoff": {
            "target_agent": AgentType.DATA,
            "task_description": "查询企业网银当前功能",
        },
        "handoff_queue": [
            {
                "target_agent": AgentType.TODO,
                "task_description": "创建待办：整理网银功能清单",
            }
        ],
        "completed_handoffs": [],
        "handoff_execution_trace": [],
        "multi_intent_mode": True,
        "iteration_count": 0,
    }

    decision = _evaluate_handoff_progress(state)

    assert decision["evaluation"] == "continue"
    assert decision["evaluation_route"] == "todo_expert"
    assert decision["pending_handoff"]["target_agent"] == AgentType.TODO
    assert decision["handoff_queue"] == []
    assert len(decision["completed_handoffs"]) == 1
    assert len(decision["handoff_execution_trace"]) == 1


def test_evaluate_handoff_progress_enters_coverage_gate_after_last_handoff() -> None:
    """复合任务最后一个专家完成后应先进入 coverage_gate，而不是直接 postprocess。"""
    state = {
        "messages": [
            HumanMessage(content="嘉兴天气、网银功能、并创建待办"),
            AIMessage(content="待办已创建：本周五17:00提交网银功能汇总。"),
        ],
        "pending_handoff": {
            "target_agent": AgentType.TODO,
            "task_description": "创建待办：提交网银功能汇总",
        },
        "handoff_queue": [],
        "completed_handoffs": [
            {
                "target_agent": AgentType.DATA,
                "task_description": "查询网银功能",
            }
        ],
        "handoff_execution_trace": [
            {
                "target_agent": AgentType.DATA,
                "task_description": "查询网银功能",
                "result_excerpt": "已返回企业网银功能列表",
            }
        ],
        "multi_intent_mode": True,
        "iteration_count": 1,
    }

    decision = _evaluate_handoff_progress(state)

    assert decision["evaluation"] == "coverage"
    assert decision["evaluation_route"] == "coverage_gate"
    assert decision["pending_handoff"] is None
    assert len(decision["handoff_execution_trace"]) == 2


def test_evaluate_handoff_progress_routes_direct_plus_single_expert_to_coverage() -> None:
    """direct tool + 1 个专家也应进入 coverage_gate，避免直接结束丢失完整性校验。"""
    state = {
        "messages": [
            HumanMessage(content="嘉兴天气并创建待办"),
            ToolMessage(
                content='{"answer":"嘉兴今天多云，气温 18-24 摄氏度"}',
                tool_call_id="t1",
                name="tavily_search",
            ),
            AIMessage(content="待办已创建：明天 10:00 跟进天气变化。"),
        ],
        "pending_handoff": {
            "target_agent": AgentType.TODO,
            "task_description": "创建待办：跟进嘉兴天气变化",
        },
        "handoff_queue": [],
        "completed_handoffs": [],
        "handoff_execution_trace": [],
        "multi_intent_mode": True,
        "iteration_count": 0,
    }

    decision = _evaluate_handoff_progress(state)

    assert decision["evaluation"] == "coverage"
    assert decision["evaluation_route"] == "coverage_gate"
    assert decision["pending_handoff"] is None
    assert len(decision["handoff_execution_trace"]) == 1


def test_evaluate_handoff_progress_enters_coverage_gate_when_coverage_missing() -> None:
    """复合任务存在未完成目标时，应统一进入 coverage_gate 决策下一跳。"""
    state = {
        "messages": [
            HumanMessage(content="先查待办 + 再看天气"),
            AIMessage(content="查到 1 条待办：提交周报"),
        ],
        "pending_handoff": {
            "target_agent": AgentType.TODO,
            "task_description": "查询待办",
        },
        "handoff_queue": [],
        "completed_handoffs": [],
        "handoff_execution_trace": [],
        "multi_intent_mode": True,
        "iteration_count": 0,
        "system_context": "当前时间: 2026-02-27 20:00:00 (Friday)",
        "decomposed_goals": [
            {"goal_id": "GOAL-01", "order": 1, "kind": "todo.query", "title": "待办事项", "must_answer": True},
            {"goal_id": "GOAL-02", "order": 2, "kind": "external.lookup", "title": "外部信息", "must_answer": True},
        ],
    }

    decision = _evaluate_handoff_progress(state)

    assert decision["evaluation"] == "coverage"
    assert decision["evaluation_route"] == "coverage_gate"
    assert decision["pending_handoff"] is None
    assert decision["handoff_queue"] == []
    assert "iteration_count" not in decision
    assert decision["coverage_report"]["pass"] is False
    assert decision["delivery_meta"]["pending_goal_titles"] == ["外部信息"]


def test_build_multi_intent_summary_content_contains_direct_and_expert_results() -> None:
    """统一汇总应覆盖 direct tool 与专家执行结果，并隐藏内部术语。"""
    state = {
        "messages": [
            ToolMessage(
                content='{"answer":"嘉兴今天多云，气温 18-24 摄氏度"}',
                tool_call_id="t1",
                name="tavily_search",
            ),
            ToolMessage(
                content="企业网银目前支持账户管理、转账、批量代发等功能。",
                tool_call_id="t2",
                name="knowledge_search",
            ),
        ],
        "handoff_execution_trace": [
            {
                "target_agent": AgentType.DATA,
                "task_description": "确认企业网银功能",
                "result_excerpt": "已确认三项核心功能",
            },
            {
                "target_agent": AgentType.TODO,
                "task_description": "创建待办：周五17:00输出汇总",
                "result_excerpt": "待办已创建成功",
            },
        ],
    }

    summary = _build_multi_intent_summary_content(state)

    assert "外部信息" in summary
    assert "待办事项" in summary
    assert "待办已创建成功" in summary
    assert "data_expert" not in summary
    assert "todo_expert" not in summary
    assert "handoff" not in summary.lower()


def test_build_delivery_artifacts_includes_direct_answer_markdown_when_handoff_exists() -> None:
    """存在 handoff 时，仍应保留 Supervisor 已完成的用户可见 Markdown。"""
    state = {
        "messages": [HumanMessage(content="先回答预算，再查待办")],
        "handoff_execution_trace": [
            {
                "goal_id": "GOAL-02",
                "target_agent": AgentType.TODO,
                "task_description": "查询待办",
                "direct_answer_markdown": "预算控制建议：\n- 先核对本月支出上限。",
                "result_excerpt": "查到 1 条待办",
            }
        ],
    }

    deliverables = _build_delivery_artifacts(state)
    general_deliverables = [item for item in deliverables if item.get("kind") == "general.reply"]

    assert general_deliverables
    assert general_deliverables[0]["payload"]["display_markdown"] == "预算控制建议：\n- 先核对本月支出上限。"
    assert "预算控制建议" in str(general_deliverables[0].get("summary") or "")


def test_build_multi_intent_summary_content_respects_user_question_order() -> None:
    """最终汇总应优先按用户提问顺序组织答案，而不是执行顺序。"""
    state = {
        "messages": [
            HumanMessage(content="先帮我看看嘉兴天气，再查一下我的待办"),
            ToolMessage(
                content='{"answer":"嘉兴今天多云，18-24℃"}',
                tool_call_id="t1",
                name="tavily_search",
            ),
            AIMessage(
                content="查到 1 条待办",
                additional_kwargs={
                    "data_type": "todo_list",
                    "data": {"todos": [{"title": "提交周报", "status": "todo"}]},
                },
            ),
        ],
        "handoff_execution_trace": [
            {
                "target_agent": AgentType.TODO,
                "task_description": "查询待办",
                "result_excerpt": "查到 1 条待办",
            }
        ],
    }

    summary = _build_multi_intent_summary_content(state)
    first_line = summary.splitlines()[1]
    second_line = summary.splitlines()[2]

    assert "外部信息" in first_line
    assert "待办事项" in second_line


def test_resolve_coverage_gate_route_returns_supervisor_when_missing_goals() -> None:
    """coverage 未通过时应先回到 supervisor 继续补齐。"""
    route = _resolve_coverage_gate_route(
        state={"coverage_retry_count": 0},
        coverage_report={
            "pass": False,
            "missing_goals": [{"goal_id": "GOAL-02", "title": "外部信息", "reason": "missing_deliverable"}],
        },
    )

    assert route["route"] == "supervisor"
    assert route["coverage_retry_count"] == 1
    assert route["retry_exhausted"] is False


def test_resolve_coverage_gate_route_allows_partial_gap_for_subagent_only_missing() -> None:
    """仅专家目标缺失时，应允许直接进入 final_composer（A1 策略）。"""
    active_goals = [
        {
            "goal_id": "GOAL-01",
            "order": 1,
            "kind": "general.reply",
            "title": "问题回复",
            "must_answer": True,
            "allowed_agents": [],
        },
        {
            "goal_id": "GOAL-02",
            "order": 2,
            "kind": "todo.query",
            "title": "待办事项",
            "must_answer": True,
            "allowed_agents": [AgentType.TODO],
        },
    ]
    route = _resolve_coverage_gate_route(
        state={"coverage_retry_count": 0},
        active_goals=active_goals,
        coverage_report={
            "pass": False,
            "missing_goals": [{"goal_id": "GOAL-02", "title": "待办事项", "reason": "missing_deliverable"}],
        },
    )

    assert route["route"] == "final_composer"
    assert route["partial_gap_allowed"] is True
    assert route["coverage_retry_count"] == 0


def test_resolve_coverage_gate_route_enters_postprocess_after_retry_exhausted(monkeypatch) -> None:
    """补齐轮次超过上限后应转入 postprocess 输出缺口说明。"""
    monkeypatch.setenv("COVERAGE_GATE_MAX_RETRIES", "1")

    route = _resolve_coverage_gate_route(
        state={"coverage_retry_count": 1},
        coverage_report={
            "pass": False,
            "missing_goals": [{"goal_id": "GOAL-02", "title": "外部信息", "reason": "missing_deliverable"}],
        },
    )

    assert route["route"] == "postprocess"
    assert route["coverage_retry_count"] == 2
    assert route["retry_exhausted"] is True


def test_resolve_coverage_gate_route_goes_final_when_passed() -> None:
    """coverage 通过时应进入 final_composer。"""
    route = _resolve_coverage_gate_route(
        state={"coverage_retry_count": 2},
        coverage_report={"pass": True, "missing_goals": []},
    )

    assert route["route"] == "final_composer"
    assert route["coverage_retry_count"] == 0


def test_compute_coverage_report_should_fill_goal_id_for_direct_deliverable() -> None:
    """direct tool 交付物未显式携带 goal_id 时，coverage 输出仍应满足合同。"""
    active_goals = [
        {"goal_id": "GOAL-01", "order": 1, "kind": "todo.query", "title": "待办事项", "must_answer": True},
        {"goal_id": "GOAL-02", "order": 2, "kind": "external.lookup", "title": "外部信息", "must_answer": True},
    ]
    deliverables = [
        {
            "kind": "external.lookup",
            "status": "success",
            "summary": "嘉兴今天多云，18-24℃",
            "payload": {"findings": [{"label": "天气", "summary": "多云"}]},
        },
        {
            "goal_id": "GOAL-01",
            "kind": "todo.query",
            "status": "success",
            "summary": "查到 1 条待办",
            "payload": {"todos": [{"title": "提交周报"}]},
        },
    ]

    report = _compute_coverage_report(active_goals, deliverables)
    normalized, valid, error = validate_coverage_report_contract(report)

    assert report["pass"] is True
    assert valid is True
    assert error == ""
    assert normalized["goal_results"]["GOAL-02"]["goal_id"] == "GOAL-02"


def test_build_delivery_artifacts_marks_data_query_failed_without_sql_result() -> None:
    """data_expert 只返回失败文本、未产出 sql_result 时，不应算作已完成覆盖。"""
    state = {
        "messages": [
            HumanMessage(content="查询2025年6月30日贷款余额前10名的客户"),
            AIMessage(content="请确认是否只执行贷款余额查询？"),
        ],
        "handoff_execution_trace": [
            {
                "goal_id": "GOAL-01",
                "target_agent": AgentType.DATA,
                "task_description": "查看2025-06-30贷款余额前10名客户",
                "result_excerpt": "请确认是否只执行贷款余额查询？",
            }
        ],
    }
    active_goals = [
        {
            "goal_id": "GOAL-01",
            "order": 1,
            "kind": "data.query",
            "title": "数据查询",
            "must_answer": True,
        }
    ]

    deliverables = _build_delivery_artifacts(state)
    data_deliverable = next(item for item in deliverables if item.get("kind") == "data.query")
    report = _compute_coverage_report(active_goals, deliverables)

    assert data_deliverable["status"] == "failed"
    assert report["pass"] is False
    assert report["missing_goals"][0]["goal_id"] == "GOAL-01"
    assert report["goal_attempts"]["GOAL-01"]["status"] == "failed"
    assert report["goal_attempts"]["GOAL-01"]["payload"]["failure_message"] == "请确认是否只执行贷款余额查询？"


def test_render_final_answer_should_use_failed_goal_attempt_message() -> None:
    """missing goal 若已有失败尝试证据，最终答复应直接带出失败原因。"""
    active_goals = [
        {"goal_id": "GOAL-01", "order": 1, "kind": "data.query", "title": "数据查询", "must_answer": True},
        {"goal_id": "GOAL-02", "order": 2, "kind": "external.lookup", "title": "嘉兴天气", "must_answer": True},
    ]
    coverage_report = {
        "pass": False,
        "missing_goals": [
            {"goal_id": "GOAL-01", "title": "数据查询", "reason": "missing_deliverable"},
        ],
        "goal_results": {
            "GOAL-02": {
                "goal_id": "GOAL-02",
                "kind": "external.lookup",
                "status": "success",
                "summary": "嘉兴天气晴到多云",
                "payload": {"display_markdown": "嘉兴天气：\n- 今天（03-08）：多云"},
            }
        },
        "goal_attempts": {
            "GOAL-01": {
                "goal_id": "GOAL-01",
                "kind": "data.query",
                "status": "failed",
                "summary": "数据子任务解析依赖的模型当前不可用，请稍后重试。",
                "payload": {"failure_message": "数据子任务解析依赖的模型当前不可用，请稍后重试。"},
            }
        },
    }

    answer = _render_final_answer(active_goals, coverage_report)

    assert "1. 数据查询：暂未完成，数据子任务解析依赖的模型当前不可用，请稍后重试。" in answer
    assert "2. 嘉兴天气：" in answer
    assert "- 今天（03-08）：多云" in answer


def test_build_delivery_artifacts_should_prefer_weather_result_over_news_portal_noise() -> None:
    """Tavily 首条若是新闻噪声，也应优先选择真正的天气站结果。"""
    state = {
        "messages": [
            HumanMessage(content="查询嘉兴天气"),
            ToolMessage(
                content='{"results":[{"url":"https://www.163.com/dy/article/test.html","title":"刚刚确认，即将抵达嘉兴，持续一周 - 网易","content":"娱乐 财经 汽车 科技 时尚。特别声明：以上内容为自媒体平台发布。"},{"url":"https://www.1543.net/jiaxing_houtian","title":"【嘉兴72小时实时天气】嘉兴后天天气_嘉兴后天的天气情况_1543天气网","content":"| 2026年02月01日（星期日） |  | 多云转晴 | 0℃ ~ 8℃ | 北风转西风 | <3级 |. | 2026年02月02日（星期一） |  | 晴 | 1℃ ~ 11℃ | 北风转东风 | <3级 |."}]}' ,
                tool_call_id="t-rank",
                name="tavily_search",
            ),
        ],
        "handoff_execution_trace": [],
    }

    deliverables = _build_delivery_artifacts(state)
    external_deliverable = next(item for item in deliverables if item.get("kind") == "external.lookup")
    display_markdown = external_deliverable["payload"]["display_markdown"]

    assert display_markdown.startswith("嘉兴天气：")
    assert "网易" not in display_markdown
    assert "多云转晴" in display_markdown


def test_build_delivery_artifacts_should_generate_weather_markdown_from_tavily_page_content() -> None:
    """天气网页结果应直接规整成富文本，而不是原始站点噪声。"""
    state = {
        "messages": [
            HumanMessage(content="查询嘉兴天气"),
            ToolMessage(
                content='{"results":[{"title":"嘉兴天气预报,嘉兴7天天气预报,嘉兴天气查询","content":"台风路径 空间天气 图片 专题 环境 旅游 碳中和 气象科普 一带一路 产创平台 嘉兴 [切换] 当前时间：2026-03-08周日13:01 空气 优 东南风 3级 今天 (03-08) 多云 东风 微风 明天 (03-09) 多云 东北风 微风 周二 (03-10) 小雨 13/10℃ 东风 微风 周三 (03-11) 阴 12/8℃ 东风 微风"}]}' ,
                tool_call_id="t-weather",
                name="tavily_search",
            ),
        ],
        "handoff_execution_trace": [],
    }

    deliverables = _build_delivery_artifacts(state)
    external_deliverable = next(item for item in deliverables if item.get("kind") == "external.lookup")
    display_markdown = external_deliverable["payload"]["display_markdown"]

    assert display_markdown.startswith("嘉兴天气：")
    assert "今天（03-08）" in display_markdown
    assert "明天（03-09）" in display_markdown
    assert "周二（03-10）" in display_markdown
    assert "台风路径" not in display_markdown
    assert "台风路径" not in external_deliverable["summary"]


def test_build_delivery_artifacts_should_parse_weather_table_rows_from_1543_content() -> None:
    """1543 天气网这类表格行内容，也应规整成天气段 Markdown。"""
    state = {
        "messages": [
            HumanMessage(content="查询嘉兴天气"),
            ToolMessage(
                content='{"results":[{"title":"【嘉兴72小时实时天气】嘉兴后天天气_嘉兴后天的天气情况_1543天气网","content":"* 嘉兴市气象局03日（星期二) 7时预计，嘉兴明日天气晴，最低气温3℃，最高气温11℃，东风转南风<3级，1543天气网提醒您密切关注嘉兴后天天气。 | 2026年02月01日（星期日） |  | 多云转晴 | 0℃ ~ 8℃ | 北风转西风 | <3级 |. | 2026年02月02日（星期一） |  | 晴 | 1℃ ~ 11℃ | 北风转东风 | <3级 |. | 2026年02月03日（星期二） |  | 晴 | 3℃ ~ 11℃ | 东风转南风 | <3级 |."}]}' ,
                tool_call_id="t-1543",
                name="tavily_search",
            ),
        ],
        "handoff_execution_trace": [],
    }

    deliverables = _build_delivery_artifacts(state)
    external_deliverable = next(item for item in deliverables if item.get("kind") == "external.lookup")
    display_markdown = external_deliverable["payload"]["display_markdown"]

    assert display_markdown.startswith("嘉兴天气：")
    assert "2026年02月01日(星期日)" in display_markdown
    assert "多云转晴" in display_markdown
    assert "0℃~8℃" in display_markdown
    assert "1543天气网提醒" not in display_markdown



def test_build_delivery_artifacts_should_parse_weather_forecast_dot_com_content() -> None:
    """weather-forecast.com 这类英文天气页，也应规整成多行天气段。"""
    state = {
        "messages": [
            HumanMessage(content="查询嘉兴天气"),
            ToolMessage(
                content='{"results":[{"title":"嘉兴天气预报","content":"嘉兴 今日天气 (1–3 天数): Mostly dry. Very mild (max 12°C on Fri afternoon, min 3°C on Sat morning). Wind will be generally light. 嘉兴 天气 (4–7 天数): Mostly dry. Very mild (max 16°C on Wed afternoon, min 3°C on Tue morning). Wind will be generally light."}]}' ,
                tool_call_id="t-forecast-en",
                name="tavily_search",
            ),
        ],
        "handoff_execution_trace": [],
    }

    deliverables = _build_delivery_artifacts(state)
    external_deliverable = next(item for item in deliverables if item.get("kind") == "external.lookup")
    display_markdown = external_deliverable["payload"]["display_markdown"]

    assert display_markdown.startswith("嘉兴天气：")
    assert "今日（1-3天）" in display_markdown
    assert "3°C~12°C" in display_markdown
    assert "4-7天" in display_markdown
    assert "Mostly dry" in display_markdown



def test_build_delivery_artifacts_should_scan_all_weather_results_before_fallback() -> None:
    """首条结果若只有站点导航噪声，也应继续选择后续可结构化天气结果。"""
    state = {
        "messages": [
            HumanMessage(content="查询嘉兴天气"),
            ToolMessage(
                content='{"results":[{"title":"嘉兴天气预报,嘉兴7天天气预报,嘉兴15天天气预报,嘉兴天气查询","content":"台风路径 空间天气 图片 专题 环境 旅游 碳中和 气象科普 一带一路 产创平台 热门城市 热门景点 选择省市 高清图集"},{"title":"嘉兴市天气预报_天气查询- 墨迹天气","content":"嘉兴市， 浙江省， 中国 今天 多云 多云 7° / 10° 北风 3级 46 优 明天 小雨 小雨 8° / 11° 东南风 3级 40 优"}]}' ,
                tool_call_id="t-weather-mixed",
                name="tavily_search",
            ),
        ],
        "handoff_execution_trace": [],
    }

    deliverables = _build_delivery_artifacts(state)
    external_deliverable = next(item for item in deliverables if item.get("kind") == "external.lookup")
    display_markdown = external_deliverable["payload"]["display_markdown"]

    assert display_markdown.startswith("嘉兴市天气：")
    assert "今天" in display_markdown
    assert "明天" in display_markdown
    assert "台风路径" not in display_markdown


def test_build_delivery_artifacts_should_wrap_weather_summary_fallback_as_weather_block() -> None:
    """天气类结果即使只有一句摘要，也应保持天气段格式，而不是标题正文平铺。"""
    state = {
        "messages": [
            HumanMessage(content="查询嘉兴天气"),
            ToolMessage(
                content='{"results":[{"title":"嘉兴市未来30天天气预报","content":"嘉兴市 ... 未来30天将有19天下雨，最高温21°（03月22日），最低温2°（03月09日）。"}]}' ,
                tool_call_id="t-weather-summary",
                name="tavily_search",
            ),
        ],
        "handoff_execution_trace": [],
    }

    deliverables = _build_delivery_artifacts(state)
    external_deliverable = next(item for item in deliverables if item.get("kind") == "external.lookup")
    display_markdown = external_deliverable["payload"]["display_markdown"]

    assert display_markdown.startswith("嘉兴市天气：")
    assert "- 摘要：" in display_markdown
    assert "未来30天将有19天下雨" in display_markdown


def test_build_multi_intent_summary_content_should_avoid_external_label_chain_and_markdown_noise() -> None:
    """外部信息摘要应避免重复标签链和 Markdown 噪声。"""
    state = {
        "messages": [
            HumanMessage(content="查询嘉兴近一周天气"),
            ToolMessage(
                content='{"results":[{"title":"嘉兴天气预报7天：反馈","content":"## 嘉兴 今日天气 (1-3 天数): Mostly dry. Very mild."}]}',
                tool_call_id="t1",
                name="tavily_search",
            ),
        ],
    }

    summary = _build_multi_intent_summary_content(state)
    first_line = summary.splitlines()[1]

    assert "天气/实时信息：" not in first_line
    assert "##" not in summary
    assert "嘉兴" in summary
    assert "Mostly dry" in summary


def test_render_coverage_blocked_message_should_not_prompt_user_to_continue() -> None:
    """coverage 缺口属于内部补齐失败，不应再要求用户回复“继续”。"""
    active_goals = [
        {"goal_id": "GOAL-01", "order": 1, "kind": "todo.query", "title": "待办事项", "must_answer": True},
        {"goal_id": "GOAL-02", "order": 2, "kind": "external.lookup", "title": "外部信息", "must_answer": True},
    ]
    coverage_report = {
        "pass": False,
        "missing_goals": [
            {"goal_id": "GOAL-02", "title": "外部信息", "reason": "missing_deliverable"},
        ],
    }

    message = _render_coverage_blocked_message(active_goals, coverage_report)

    assert "- 外部信息" in message
    assert "继续补齐" not in message
    assert "你回复“继续”即可" not in message
    assert "请稍后重试" in message


def test_render_final_answer_should_not_invite_user_to_continue_when_missing_goals() -> None:
    """partial gap 收口时可以提示重试，但不应邀请用户继续内部补齐。"""
    active_goals = [
        {"goal_id": "GOAL-01", "order": 1, "kind": "data.query", "title": "数据查询", "must_answer": True},
    ]
    coverage_report = {
        "pass": False,
        "missing_goals": [
            {"goal_id": "GOAL-01", "title": "数据查询", "reason": "missing_deliverable"},
        ],
        "goal_results": {},
    }

    answer = _render_final_answer(active_goals, coverage_report)

    assert "数据查询：暂未完成，缺少可用结果。" in answer
    assert "如果你愿意，我可以继续补齐" not in answer
    assert "请稍后重试" in answer


def test_build_delivery_artifacts_should_prefer_direct_answer_markdown_over_tool_fallback() -> None:
    """external.lookup 正文应优先保留直答 Markdown，而不是再从 tool 结果猜格式。"""
    state = {
        "messages": [
            HumanMessage(content="查询嘉兴天气，再查贷款余额"),
            ToolMessage(
                content='{"results":[{"title":"嘉兴天气预报","content":"| 嘉兴 今日天气(1-3 天数) Mostly dry. Very mild."}]}',
                tool_call_id="t1",
                name="tavily_search",
            ),
        ],
        "handoff_execution_trace": [
            {
                "goal_id": "GOAL-01",
                "target_agent": AgentType.DATA,
                "task_description": "查询贷款余额",
                "result_excerpt": "查询完成",
                "direct_answer_markdown": "嘉兴天气：\n- 今日：多云，5~11℃\n- 明日：多云，2~13℃\n\n---\n\n已收到查询 **贷款余额前10名客户** 的需求，数据查询部分将由系统继续处理。",
            }
        ],
    }

    deliverables = _build_delivery_artifacts(state)
    external_deliverable = next(item for item in deliverables if item.get("kind") == "external.lookup")
    display_markdown = external_deliverable["payload"]["display_markdown"]

    assert display_markdown == "嘉兴天气：\n- 今日：多云，5~11℃\n- 明日：多云，2~13℃"
    assert "Mostly dry" not in display_markdown


def test_render_final_answer_should_preserve_external_lookup_markdown_format() -> None:
    """external.lookup 应保留 display_markdown 中的换行与 Markdown 格式。"""
    active_goals = [
        {"goal_id": "GOAL-01", "order": 1, "kind": "external.lookup", "title": "查询嘉兴天气", "must_answer": True},
    ]
    deliverables = [
        {
            "goal_id": "GOAL-01",
            "kind": "external.lookup",
            "status": "success",
            "summary": "当前嘉兴天气总体晴到多云，气温温和。",
            "payload": {
                "display_markdown": "当前嘉兴天气总体**晴到多云，气温温和**。\n\n- 日间：12-13℃\n- 风险：早晨局部有霜冻预警",
                "findings": [{"label": "天气/实时信息", "summary": "嘉兴天气总体晴到多云"}],
            },
        }
    ]

    coverage_report = _compute_coverage_report(active_goals, deliverables)
    answer = _render_final_answer(active_goals, coverage_report)

    assert "1. 查询嘉兴天气：" in answer
    assert "    当前嘉兴天气总体**晴到多云，气温温和**。" in answer
    assert "    - 日间：12-13℃" in answer
    assert "    - 风险：早晨局部有霜冻预警" in answer
