"""Progressive load_skills 工具专项测试。"""

import json
from types import SimpleNamespace

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

from app.ai.tools import ragflow_tool
from app.ai.state import AgentType
from app.ai.workflow import multi_agent_graph
from app.services.skill_service import SkillService


def test_get_supervisor_tools_registers_load_skills_in_progressive_mode(monkeypatch) -> None:
    """progressive mode 下 Supervisor 必须显式暴露 load_skills 工具。"""

    monkeypatch.setattr(multi_agent_graph, "_get_common_tool_entries", lambda: [])
    monkeypatch.setattr(
        multi_agent_graph,
        "_apply_tool_governance_policy",
        lambda entries, agent_name: [entry["tool"] for entry in entries],
    )
    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )

    tools = multi_agent_graph._get_supervisor_tools()

    assert any(getattr(tool, "name", "") == "load_skills" for tool in tools)


def test_get_runtime_visible_supervisor_tools_hides_skill_owned_tool_before_load(monkeypatch) -> None:
    """progressive mode 下，skill-owned 领域工具在未加载前不应暴露给当前轮模型。"""

    @tool("knowledge_search")
    def knowledge_tool() -> str:
        """测试知识检索工具。"""
        return "KB"

    @tool("load_skills")
    def load_tool() -> str:
        """测试技能加载工具。"""
        return "LOAD"

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )
    monkeypatch.setattr(
        multi_agent_graph,
        "_apply_tool_governance_policy",
        lambda entries, agent_name: [entry["tool"] for entry in entries],
    )

    tools = multi_agent_graph._get_runtime_visible_supervisor_tools(
        state={"allowed_tool_registry": {}},
        tool_entries=[
            multi_agent_graph._build_tool_entry(
                knowledge_tool,
                {"group:knowledge"},
                runtime_visibility="after_load",
                required_runtime_tools={"knowledge_search"},
            ),
            multi_agent_graph._build_tool_entry(load_tool, {"group:skill"}),
        ],
    )

    tool_names = [getattr(item, "name", "") for item in tools]
    assert "load_skills" in tool_names
    assert "knowledge_search" not in tool_names


def test_get_runtime_visible_supervisor_tools_reveals_skill_owned_tool_after_load(monkeypatch) -> None:
    """progressive mode 下，skill-owned 领域工具在授权后应进入当前轮模型可见集合。"""

    @tool("knowledge_search")
    def knowledge_tool() -> str:
        """测试知识检索工具。"""
        return "KB"

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )
    monkeypatch.setattr(
        multi_agent_graph,
        "_apply_tool_governance_policy",
        lambda entries, agent_name: [entry["tool"] for entry in entries],
    )

    tools = multi_agent_graph._get_runtime_visible_supervisor_tools(
        state={
            "allowed_tool_registry": {
                "knowledge_search": {
                    "tool_name": "knowledge_search",
                    "skill_ids": ["knowledge-search"],
                    "versions": ["v1"],
                }
            }
        },
        tool_entries=[
            multi_agent_graph._build_tool_entry(
                knowledge_tool,
                {"group:knowledge"},
                runtime_visibility="after_load",
                required_runtime_tools={"knowledge_search"},
            )
        ],
    )

    assert [getattr(item, "name", "") for item in tools] == ["knowledge_search"]


def test_load_skills_tool_updates_registry_allowed_tools_and_tool_message(monkeypatch) -> None:
    """load_skills 工具应回写 loaded_skill_registry/allowed_tool_registry，并携带 canonical skill_runtime。"""

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )
    monkeypatch.setattr(
        SkillService,
        "load_skills_for_session",
        classmethod(
            lambda cls, **kwargs: {
                "requested_skill_ids": ["knowledge-search"],
                "loaded_skills": [
                    {
                        "skill_id": "knowledge-search",
                        "effective_version": "v1",
                        "content": "# Knowledge Search\n正文",
                        "truncated": False,
                    }
                ],
                "errors": [],
                "truncated_count": 0,
                "loaded_skill_registry": {
                    "knowledge-search": {
                        "skill_id": "knowledge-search",
                        "version": "v1",
                        "truncated": False,
                        "source_turn_id": kwargs.get("source_turn_id"),
                    }
                },
                "allowed_tool_registry": {
                    "knowledge_search": {
                        "tool_name": "knowledge_search",
                        "skill_ids": ["knowledge-search"],
                        "versions": ["v1"],
                    }
                },
                "loaded_skill_context": "以下技能正文已加载到当前会话，可直接复用：\n\n### Knowledge Search | skill_id=knowledge-search | version=v1\n# Knowledge Search\n正文",
                "catalog_version": "cat-001",
                "visible_skill_count": 1,
                "missing_skills": [],
            }
        ),
    )

    tool = multi_agent_graph._create_load_skills_tool()
    command = tool.func(
        skill_ids=["knowledge-search"],
        reason="需要知识库能力",
        state={
            "messages": [],
            "user_id": 7,
            "turn_id": "turn-001",
            "catalog_version": "cat-001",
            "visible_skill_count": 1,
            "skill_catalog_manifest": [{"skill_id": "knowledge-search", "effective_version": "v1"}],
        },
        tool_call_id="tc-001",
    )

    assert isinstance(command, Command)
    assert command.update["loaded_skill_registry"]["knowledge-search"]["version"] == "v1"
    assert command.update["allowed_tool_registry"]["knowledge_search"]["tool_name"] == "knowledge_search"
    assert command.update["loaded_skill_context"].startswith("以下技能正文已加载到当前会话")

    message = command.update["messages"][0]
    payload = json.loads(message.content)
    assert payload["requested_skill_ids"] == ["knowledge-search"]
    assert message.name == "load_skills"
    assert message.additional_kwargs["skill_runtime"]["loaded_skills"][0]["skill_id"] == "knowledge-search"
    assert message.additional_kwargs["skill_runtime"]["allowed_tools"] == ["knowledge_search"]
    assert message.additional_kwargs["skill_runtime"]["replay_source"] == "live"


def test_apply_router_contract_guard_falls_back_to_single_goal_query(monkeypatch) -> None:
    """单目标数据查询即使未显式写入 decomposed_goals，也应能放行 data_expert handoff。"""

    monkeypatch.setattr(multi_agent_graph, "_is_router_contract_guard_enabled", lambda: True)

    accepted, blocked, pending = multi_agent_graph._apply_router_contract_guard(
        [
            {
                "target_agent": AgentType.DATA,
                "task_description": "用户原始问题：查询2025年6月30日贷款余额前10名的客户",
            }
        ],
        state={
            "messages": [
                __import__("langchain_core.messages", fromlist=["HumanMessage"]).HumanMessage(
                    content="查询2025年6月30日贷款余额前10名的客户"
                )
            ]
        },
    )

    assert len(accepted) == 1
    assert blocked == []
    assert pending == []
    assert accepted[0]["goal_id"] == "GOAL-01"


def test_build_handoff_status_message_returns_targeted_copy() -> None:
    """handoff 状态文案应区分内建专家与通用专家。"""

    assert multi_agent_graph._build_handoff_status_message(AgentType.DATA) == "已识别为数据查询，正在委派 data_expert。"
    assert multi_agent_graph._build_handoff_status_message(AgentType.TODO) == "已识别为待办请求，正在委派 todo_expert。"
    assert multi_agent_graph._build_handoff_status_message("report_expert") == "正在委派 report_expert。"


def test_runtime_tool_call_wrapper_blocks_unauthorized_skill_owned_tool(monkeypatch) -> None:
    """执行层应统一拦截未授权的 skill-owned tool call。"""

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )

    entries = [
        multi_agent_graph._build_tool_entry(
            ragflow_tool.knowledge_search,
            {"group:knowledge"},
            runtime_visibility="after_load",
            required_runtime_tools={"knowledge_search"},
        )
    ]
    wrap, _ = multi_agent_graph._build_runtime_tool_call_wrapper(entries, agent_name="supervisor")

    request = SimpleNamespace(
        tool_call={"id": "tc-knowledge", "name": "knowledge_search", "args": {"query": "请假流程"}},
        runtime=SimpleNamespace(state={"allowed_tool_registry": {}}),
        state={"allowed_tool_registry": {}},
    )

    result = wrap(request, lambda _request: "SHOULD_NOT_RUN")

    assert isinstance(result, ToolMessage)
    assert "请先调用 load_skills" in str(result.content)
    assert result.name == "knowledge_search"


def test_runtime_tool_call_wrapper_allows_authorized_skill_owned_tool(monkeypatch) -> None:
    """执行层在已授权后应放行 skill-owned tool call。"""

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )

    entries = [
        multi_agent_graph._build_tool_entry(
            ragflow_tool.knowledge_search,
            {"group:knowledge"},
            runtime_visibility="after_load",
            required_runtime_tools={"knowledge_search"},
        )
    ]
    wrap, _ = multi_agent_graph._build_runtime_tool_call_wrapper(entries, agent_name="supervisor")

    request = SimpleNamespace(
        tool_call={"id": "tc-knowledge", "name": "knowledge_search", "args": {"query": "请假流程"}},
        runtime=SimpleNamespace(
            state={
                "allowed_tool_registry": {
                    "knowledge_search": {
                        "tool_name": "knowledge_search",
                        "skill_ids": ["knowledge-search"],
                        "versions": ["v1"],
                    }
                }
            }
        ),
        state={},
    )

    result = wrap(request, lambda _request: "KB_OK")

    assert result == "KB_OK"


def test_get_runtime_visible_supervisor_handoff_tools_hides_data_handoff_before_load(monkeypatch) -> None:
    """progressive mode 下，data handoff 在未加载数据 skill 前不应暴露。"""

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )
    monkeypatch.setattr(
        multi_agent_graph,
        "_apply_tool_governance_policy",
        lambda entries, agent_name: [entry["tool"] for entry in entries],
    )

    tools = multi_agent_graph._get_runtime_visible_supervisor_handoff_tools(
        state={"allowed_tool_registry": {}},
        tool_entries=[
            multi_agent_graph._build_tool_entry(
                multi_agent_graph._create_task_handoff_tool(AgentType.DATA, "data"),
                {"group:handoff"},
                runtime_visibility="after_load",
                required_runtime_tools={"assign_to_data_expert"},
            )
        ],
    )

    assert [getattr(item, "name", "") for item in tools] == []


def test_get_runtime_visible_supervisor_handoff_tools_reveals_data_handoff_after_load(monkeypatch) -> None:
    """progressive mode 下，data handoff 在加载数据 skill 后应暴露。"""

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )
    monkeypatch.setattr(
        multi_agent_graph,
        "_apply_tool_governance_policy",
        lambda entries, agent_name: [entry["tool"] for entry in entries],
    )

    tools = multi_agent_graph._get_runtime_visible_supervisor_handoff_tools(
        state={
            "allowed_tool_registry": {
                "assign_to_data_expert": {
                    "tool_name": "assign_to_data_expert",
                    "skill_ids": ["sql-expert"],
                    "versions": ["v1"],
                }
            }
        },
        tool_entries=[
            multi_agent_graph._build_tool_entry(
                multi_agent_graph._create_task_handoff_tool(AgentType.DATA, "data"),
                {"group:handoff"},
                runtime_visibility="after_load",
                required_runtime_tools={"assign_to_data_expert"},
            )
        ],
    )

    assert [getattr(item, "name", "") for item in tools] == ["assign_to_data_expert"]


def test_runtime_tool_call_wrapper_blocks_unauthorized_data_handoff(monkeypatch) -> None:
    """执行层应统一拦截未授权的 data handoff。"""

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )

    entries = [
        multi_agent_graph._build_tool_entry(
            multi_agent_graph._create_task_handoff_tool(AgentType.DATA, "data"),
            {"group:handoff"},
            runtime_visibility="after_load",
            required_runtime_tools={"assign_to_data_expert"},
        )
    ]
    wrap, _ = multi_agent_graph._build_runtime_tool_call_wrapper(entries, agent_name="supervisor")

    request = SimpleNamespace(
        tool_call={"id": "tc-data", "name": "assign_to_data_expert", "args": {"task_description": "查余额"}},
        runtime=SimpleNamespace(state={"allowed_tool_registry": {}}),
        state={"allowed_tool_registry": {}},
    )

    result = wrap(request, lambda _request: "SHOULD_NOT_RUN")

    assert isinstance(result, ToolMessage)
    assert "请先调用 load_skills" in str(result.content)
    assert result.name == "assign_to_data_expert"



def test_get_runtime_visible_supervisor_handoff_tools_hides_goal_mismatched_todo_handoff(monkeypatch) -> None:
    """数据查询场景下，不应继续暴露 todo handoff。"""

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )
    monkeypatch.setattr(
        multi_agent_graph,
        "_apply_tool_governance_policy",
        lambda entries, agent_name: [entry["tool"] for entry in entries],
    )

    tools = multi_agent_graph._get_runtime_visible_supervisor_handoff_tools(
        state={
            "messages": [
                __import__("langchain_core.messages", fromlist=["HumanMessage"]).HumanMessage(
                    content="查询2025年6月30日贷款余额前10名的客户"
                )
            ],
            "allowed_tool_registry": {
                "assign_to_data_expert": {
                    "tool_name": "assign_to_data_expert",
                    "skill_ids": ["sql-expert"],
                    "versions": ["v1"],
                }
            },
        },
        tool_entries=[
            multi_agent_graph._build_tool_entry(
                multi_agent_graph._create_task_handoff_tool(AgentType.DATA, "data"),
                {"group:handoff"},
                runtime_visibility="after_load",
                required_runtime_tools={"assign_to_data_expert"},
            ),
            multi_agent_graph._build_tool_entry(
                multi_agent_graph._create_task_handoff_tool(AgentType.TODO, "todo"),
                {"group:handoff"},
            ),
        ],
    )

    assert [getattr(item, "name", "") for item in tools] == ["assign_to_data_expert"]



def test_get_runtime_visible_supervisor_handoff_tools_hides_handoffs_without_pending_goal(monkeypatch) -> None:
    """知识问答这类无专家目标的场景，不应再暴露任何 handoff。"""

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )
    monkeypatch.setattr(
        multi_agent_graph,
        "_apply_tool_governance_policy",
        lambda entries, agent_name: [entry["tool"] for entry in entries],
    )

    tools = multi_agent_graph._get_runtime_visible_supervisor_handoff_tools(
        state={
            "messages": [
                __import__("langchain_core.messages", fromlist=["HumanMessage"]).HumanMessage(
                    content="差旅报销规定是什么？"
                )
            ],
            "allowed_tool_registry": {
                "assign_to_todo_expert": {
                    "tool_name": "assign_to_todo_expert",
                    "skill_ids": ["todo-skill"],
                    "versions": ["v1"],
                }
            },
        },
        tool_entries=[
            multi_agent_graph._build_tool_entry(
                multi_agent_graph._create_task_handoff_tool(AgentType.TODO, "todo"),
                {"group:handoff"},
            ),
            multi_agent_graph._build_tool_entry(
                multi_agent_graph._create_task_handoff_tool(AgentType.DATA, "data"),
                {"group:handoff"},
            ),
        ],
    )

    assert tools == []


def test_build_handoff_status_message_includes_loaded_skills_for_data_expert() -> None:
    """数据专家委派状态应直接展示当前已加载的 skill。"""

    message = multi_agent_graph._build_handoff_status_message(
        AgentType.DATA,
        {
            "loaded_skill_registry": {
                "sql-expert": {"version": "v1"},
                "data-insight": {"version": "v1"},
            }
        },
    )

    assert message == "已加载 sql-expert、data-insight，正在委派 data_expert。"



def test_build_handoff_status_message_falls_back_when_no_skills_loaded() -> None:
    """无已加载 skill 时保持原有专家委派语义。"""

    assert multi_agent_graph._build_handoff_status_message(AgentType.DATA) == "已识别为数据查询，正在委派 data_expert。"



def test_load_skills_tool_should_preserve_allowed_tool_registry_when_request_is_empty(monkeypatch) -> None:
    """空 skill_ids 请求不应清空既有的领域工具授权。"""

    monkeypatch.setattr(
        SkillService,
        "load_skills_for_session",
        classmethod(
            lambda cls, **kwargs: {
                "requested_skill_ids": [],
                "loaded_skills": [],
                "errors": [],
                "truncated_count": 0,
                "loaded_skill_registry": kwargs.get("loaded_skill_registry") or {},
                "allowed_tool_registry": {},
                "loaded_skill_context": None,
                "catalog_version": kwargs.get("catalog_version"),
                "visible_skill_count": 23,
            }
        ),
    )

    tool = multi_agent_graph._create_load_skills_tool()
    command = tool.func(
        skill_ids=[],
        reason="无新增 skill",
        state={
            "messages": [],
            "user_id": 7,
            "turn_id": "turn-001",
            "catalog_version": "cat-001",
            "visible_skill_count": 23,
            "loaded_skill_registry": {
                "sql-expert": {"skill_id": "sql-expert", "version": "v1"},
            },
            "allowed_tool_registry": {
                "assign_to_data_expert": {
                    "tool_name": "assign_to_data_expert",
                    "skill_ids": ["sql-expert"],
                    "versions": ["v1"],
                }
            },
            "loaded_skill_context": "已加载 sql-expert",
        },
        tool_call_id="tc-empty-load",
    )

    assert isinstance(command, Command)
    assert command.update["allowed_tool_registry"]["assign_to_data_expert"]["tool_name"] == "assign_to_data_expert"
    assert command.update["loaded_skill_registry"]["sql-expert"]["version"] == "v1"



def test_catalog_after_load_hides_data_handoff_until_skill_loaded(monkeypatch) -> None:
    """catalog 中声明的 handoff tool_contract 应自动控制专家委派可见性。"""

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )
    monkeypatch.setattr(
        multi_agent_graph,
        "_apply_tool_governance_policy",
        lambda entries, agent_name: [entry["tool"] for entry in entries],
    )

    tool_entry = multi_agent_graph._build_tool_entry(
        multi_agent_graph._create_task_handoff_tool(AgentType.DATA, "data"),
        {"group:handoff"},
        runtime_visibility="catalog_after_load",
    )
    base_state = {
        "messages": [
            __import__("langchain_core.messages", fromlist=["HumanMessage"]).HumanMessage(
                content="查询2025年6月30日贷款余额前10名的客户"
            )
        ],
        "skill_catalog_manifest": [
            {
                "skill_id": "sql-expert",
                "tool_contract": {
                    "required_tools": ["assign_to_data_expert"],
                    "optional_tools": [],
                    "tool_groups": ["data", "handoff"],
                    "expose_after_load": True,
                },
            }
        ],
    }

    hidden = multi_agent_graph._get_runtime_visible_supervisor_handoff_tools(
        state={**base_state, "allowed_tool_registry": {}},
        tool_entries=[tool_entry],
    )
    visible = multi_agent_graph._get_runtime_visible_supervisor_handoff_tools(
        state={
            **base_state,
            "allowed_tool_registry": {
                "assign_to_data_expert": {
                    "tool_name": "assign_to_data_expert",
                    "skill_ids": ["sql-expert"],
                    "versions": ["v1"],
                }
            },
        },
        tool_entries=[tool_entry],
    )

    assert hidden == []
    assert [getattr(item, "name", "") for item in visible] == ["assign_to_data_expert"]


def test_load_skills_tool_preserves_skill_context_replay_runtime_payload(monkeypatch) -> None:
    """skill_context 回归：load_skills 仍应产出 registry 与 canonical skill_runtime。"""

    monkeypatch.setattr(
        SkillService,
        "resolve_runtime_mode",
        classmethod(lambda cls: cls.SKILL_RUNTIME_MODE_PROGRESSIVE),
    )
    monkeypatch.setattr(
        SkillService,
        "load_skills_for_session",
        classmethod(
            lambda cls, **kwargs: {
                "requested_skill_ids": ["sql-expert"],
                "loaded_skills": [
                    {
                        "skill_id": "sql-expert",
                        "effective_version": "v1",
                        "content": "# SQL Expert\n正文",
                        "truncated": False,
                    }
                ],
                "errors": [],
                "truncated_count": 0,
                "loaded_skill_registry": {
                    "sql-expert": {
                        "skill_id": "sql-expert",
                        "version": "v1",
                        "truncated": False,
                        "source_turn_id": kwargs.get("source_turn_id"),
                    }
                },
                "allowed_tool_registry": {},
                "loaded_skill_context": "已加载 sql-expert",
                "catalog_version": "cat-001",
                "visible_skill_count": 1,
                "missing_skills": [],
            }
        ),
    )

    tool = multi_agent_graph._create_load_skills_tool()
    command = tool.func(
        skill_ids=["sql-expert"],
        reason="需要 SQL 规划能力",
        state={
            "messages": [],
            "user_id": 7,
            "turn_id": "turn-002",
            "catalog_version": "cat-001",
            "visible_skill_count": 1,
            "skill_catalog_manifest": [{"skill_id": "sql-expert", "effective_version": "v1"}],
        },
        tool_call_id="tc-002",
    )

    assert command.update["loaded_skill_registry"]["sql-expert"]["version"] == "v1"
    assert command.update["loaded_skill_context"] == "已加载 sql-expert"
    message = command.update["messages"][0]
    assert message.additional_kwargs["skill_runtime"]["loaded_skills"][0]["skill_id"] == "sql-expert"
    assert message.additional_kwargs["skill_runtime"]["replay_source"] == "live"
