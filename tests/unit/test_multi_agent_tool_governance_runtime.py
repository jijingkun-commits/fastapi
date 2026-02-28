"""多智能体工具治理运行时过滤测试。"""

from app.ai.workflow.multi_agent_graph import _apply_tool_governance_policy, _build_tool_entry
from app.services.config_resolver import ConfigResolver


def read() -> str:
    return "ok"


def read_uploaded_file() -> str:
    return "ok"


def knowledge_search() -> str:
    return "ok"


def search_tool() -> str:
    return "ok"


def _tool_names(tools: list) -> list[str]:
    return [str(getattr(tool, "__name__", "")).strip() for tool in tools]


def test_apply_tool_governance_policy_returns_raw_tools_when_disabled(monkeypatch) -> None:  # noqa: ANN001
    """治理开关关闭时，应保持原工具集合。"""

    monkeypatch.setattr(
        ConfigResolver,
        "get_tool_governance_settings",
        classmethod(
            lambda cls, task_mode=None, requires_evidence=None: {
                "enabled": False,
                "fail_mode": "compat",
                "task_mode": "chat",
                "requires_evidence": False,
                "evidence_gate_enabled": False,
            }
        ),
    )

    entries = [
        _build_tool_entry(read, {"group:file"}),
        _build_tool_entry(search_tool, {"group:web"}),
    ]
    tools = _apply_tool_governance_policy(entries, agent_name="supervisor")

    assert _tool_names(tools) == ["read", "search_tool"]


def test_apply_tool_governance_policy_filters_by_allow_and_deny(monkeypatch) -> None:  # noqa: ANN001
    """allow/deny 同时存在时，deny 优先级应高于 allow。"""

    monkeypatch.setattr(
        ConfigResolver,
        "get_tool_governance_settings",
        classmethod(
            lambda cls, task_mode=None, requires_evidence=None: {
                "enabled": True,
                "fail_mode": "compat",
                "task_mode": "chat",
                "requires_evidence": False,
                "evidence_gate_enabled": False,
            }
        ),
    )
    monkeypatch.setattr(
        ConfigResolver,
        "get_tool_policy_layers",
        classmethod(
            lambda cls, agent_name: {
                "global_policy": {"allow": ["group:file"], "deny": ["read"]},
                "agent_policy": {"allow": ["knowledge_search"]},
                "merged_policy": {"allow": ["group:file", "knowledge_search"], "deny": ["read"]},
                "agent_policy_key": f"tool_governance.policy.agent.{agent_name}",
            }
        ),
    )

    entries = [
        _build_tool_entry(read, {"group:file"}),
        _build_tool_entry(read_uploaded_file, {"group:file"}),
        _build_tool_entry(knowledge_search, {"group:knowledge"}),
        _build_tool_entry(search_tool, {"group:web"}),
    ]
    tools = _apply_tool_governance_policy(entries, agent_name="supervisor")

    assert _tool_names(tools) == ["read_uploaded_file", "knowledge_search"]


def test_apply_tool_governance_policy_minimal_mode_defaults_to_strict(monkeypatch) -> None:  # noqa: ANN001
    """minimal 模式且无 allow 列表时，应默认收紧为无工具。"""

    monkeypatch.setattr(
        ConfigResolver,
        "get_tool_governance_settings",
        classmethod(
            lambda cls, task_mode=None, requires_evidence=None: {
                "enabled": True,
                "fail_mode": "minimal",
                "task_mode": "chat",
                "requires_evidence": False,
                "evidence_gate_enabled": False,
            }
        ),
    )
    monkeypatch.setattr(
        ConfigResolver,
        "get_tool_policy_layers",
        classmethod(
            lambda cls, agent_name: {
                "global_policy": {},
                "agent_policy": {},
                "merged_policy": {},
                "agent_policy_key": f"tool_governance.policy.agent.{agent_name}",
            }
        ),
    )

    entries = [
        _build_tool_entry(read_uploaded_file, {"group:file"}),
        _build_tool_entry(search_tool, {"group:web"}),
    ]
    tools = _apply_tool_governance_policy(entries, agent_name="supervisor")

    assert tools == []
