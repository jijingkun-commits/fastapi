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
    assert decision.safety_rewritten is True
    assert decision.permission_rewritten is False


@patch("app.ai.utils.sql_policy_decision.check_and_rewrite_sql")
@patch("app.ai.utils.sql_policy_decision._build_permission_scope_summary")
@patch("app.ai.utils.sql_policy_decision.sanitize_sql")
def test_policy_denied_by_permission(
    mock_sanitize_sql,
    mock_build_permission_scope_summary,
    mock_check_and_rewrite_sql,
):
    """权限检查拒绝时应返回 permission 阶段拒绝。"""

    mock_sanitize_sql.return_value = ("SELECT * FROM t", True, None)
    mock_build_permission_scope_summary.return_value = {
        "display_text": "机构：广州分行（440100）",
    }
    mock_check_and_rewrite_sql.return_value = (
        "SELECT * FROM t",
        False,
        "角色 user 无权访问表 fdmdata.f_mid_dep_tb",
    )

    decision = evaluate_sql_policy("SELECT * FROM t", user_id=9)

    assert decision.is_allowed is False
    assert decision.denied_stage == "permission"
    assert decision.reason_code == "permission_rejected"
    assert decision.permission_rewritten is False


@patch("app.ai.utils.sql_policy_decision.check_and_rewrite_sql")
@patch("app.ai.utils.sql_policy_decision._build_permission_scope_summary")
@patch("app.ai.utils.sql_policy_decision.sanitize_sql")
def test_policy_allow_with_rewritten_sql(
    mock_sanitize_sql,
    mock_build_permission_scope_summary,
    mock_check_and_rewrite_sql,
):
    """安全与权限通过时应返回重写后的 SQL。"""

    mock_sanitize_sql.return_value = ("SELECT * FROM t LIMIT 1000", True, None)
    mock_build_permission_scope_summary.return_value = {
        "org_code": "440100",
        "org_name": "广州分行",
        "display_text": "机构：广州分行（440100）",
    }
    mock_check_and_rewrite_sql.return_value = (
        "SELECT * FROM t WHERE org_code = '001' LIMIT 1000",
        True,
        None,
    )

    decision = evaluate_sql_policy("SELECT * FROM t", user_id=10)

    assert decision.is_allowed is True
    assert decision.reason_code == "allowed"
    assert "org_code" in decision.rewritten_sql
    assert decision.permission_rewritten is True
    assert decision.permission_scope_summary is not None
    assert decision.permission_scope_summary.get("display_text") == "机构：广州分行（440100）"


@patch("app.ai.utils.sql_policy_decision.check_and_rewrite_sql")
@patch("app.ai.utils.sql_policy_decision._build_permission_scope_summary")
@patch("app.ai.utils.sql_policy_decision.sanitize_sql")
def test_policy_reject_when_dept_code_missing(
    mock_sanitize_sql,
    mock_build_permission_scope_summary,
    mock_check_and_rewrite_sql,
):
    """dept_code 缺失时应返回可解释拒绝原因。"""

    mock_sanitize_sql.return_value = ("SELECT * FROM t", True, None)
    mock_build_permission_scope_summary.return_value = {
        "org_code": "440100",
        "org_name": "广州分行",
    }
    mock_check_and_rewrite_sql.return_value = (
        "SELECT * FROM t",
        False,
        "用户 7 缺少 dept_code，命中默认部门隔离策略，拒绝查询",
    )

    decision = evaluate_sql_policy("SELECT * FROM t", user_id=7)

    assert decision.is_allowed is False
    assert decision.denied_stage == "permission"
    assert decision.reason_code == "permission_rejected"
    assert "dept_code" in (decision.reason or "")
