"""SQL 统一策略决策测试。"""

from unittest.mock import patch

from app.ai.utils.sql_policy_decision import evaluate_sql_policy


@patch("app.ai.utils.sql_policy_decision.sanitize_sql")
def test_policy_denied_by_safety(mock_sanitize_sql):
    """安全检查拒绝时应直接返回拒绝结果。"""

    mock_sanitize_sql.return_value = ("SELECT * FROM t", False, "禁止访问系统 Schema: fdmdata")

    decision = evaluate_sql_policy("SELECT * FROM fdmdata.f_mid_dep_tb", user_id=1)

    assert decision.is_allowed is False
    assert decision.denied_stage == "safety"
    assert decision.reason_code == "safety_rejected"
    assert "fdmdata" in (decision.reason or "")


@patch("app.ai.utils.sql_policy_decision.sanitize_sql")
def test_policy_allow_without_user(mock_sanitize_sql):
    """缺少 user_id 时仅执行安全检查。"""

    mock_sanitize_sql.return_value = ("SELECT * FROM t LIMIT 1000", True, None)

    decision = evaluate_sql_policy("SELECT * FROM t", user_id=None)

    assert decision.is_allowed is True
    assert decision.reason_code == "allowed_without_user"
    assert decision.rewritten_sql.endswith("LIMIT 1000")


@patch("app.ai.utils.sql_policy_decision.check_and_rewrite_sql")
@patch("app.ai.utils.sql_policy_decision.sanitize_sql")
def test_policy_denied_by_permission(mock_sanitize_sql, mock_check_and_rewrite_sql):
    """权限检查拒绝时应返回 permission 阶段拒绝。"""

    mock_sanitize_sql.return_value = ("SELECT * FROM t", True, None)
    mock_check_and_rewrite_sql.return_value = (
        "SELECT * FROM t",
        False,
        "角色 user 无权访问表 fdmdata.f_mid_dep_tb",
    )

    decision = evaluate_sql_policy("SELECT * FROM t", user_id=9)

    assert decision.is_allowed is False
    assert decision.denied_stage == "permission"
    assert decision.reason_code == "permission_rejected"


@patch("app.ai.utils.sql_policy_decision.check_and_rewrite_sql")
@patch("app.ai.utils.sql_policy_decision.sanitize_sql")
def test_policy_allow_with_rewritten_sql(mock_sanitize_sql, mock_check_and_rewrite_sql):
    """安全与权限通过时应返回重写后的 SQL。"""

    mock_sanitize_sql.return_value = ("SELECT * FROM t LIMIT 1000", True, None)
    mock_check_and_rewrite_sql.return_value = (
        "SELECT * FROM t WHERE org_code = '001' LIMIT 1000",
        True,
        None,
    )

    decision = evaluate_sql_policy("SELECT * FROM t", user_id=10)

    assert decision.is_allowed is True
    assert decision.reason_code == "allowed"
    assert "org_code" in decision.rewritten_sql
