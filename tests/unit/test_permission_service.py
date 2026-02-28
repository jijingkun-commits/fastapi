"""权限服务单元测试（中文注释）。"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]


# 通过预注册轻量包，避免执行目录 __init__ 的跨模块副作用。
def _register_lightweight_package(module_name: str, relative_path: str):
    if module_name in sys.modules:
        return
    pkg = types.ModuleType(module_name)
    pkg.__path__ = [str(ROOT_DIR / relative_path)]
    sys.modules[module_name] = pkg


_register_lightweight_package("app.models", "app/models")
_register_lightweight_package("app.services", "app/services")
_register_lightweight_package("app.ai.utils", "app/ai/utils")

from app.ai.utils.permission_context import UserPermissionContext
from app.ai.utils.sql_policy_decision import SqlPolicyDecision
from app.models.data_permission import (
    DataPermissionColumn,
    DataPermissionRow,
    DataPermissionTable,
)
from app.services.permission_service import PermissionHitAudit, PermissionService


@pytest.fixture()
def permission_service() -> PermissionService:
    """提供权限服务实例并清理缓存。"""

    service = PermissionService()
    service.invalidate_cache()
    return service


def test_match_table_pattern_supports_wildcard(permission_service: PermissionService):
    """表规则应同时支持 * 与 % 通配符。"""

    assert permission_service._match_table_pattern("fdmdata.*", "fdmdata", "f_mid_dep_tb")
    assert permission_service._match_table_pattern("fdmdata.f_mid_%", "fdmdata", "f_mid_dep_tb")
    assert not permission_service._match_table_pattern("fdmdata.t_%", "sdmdata", "f_mid_dep_tb")


def test_collect_permission_hits_for_sql_tracks_allow_and_deny(permission_service: PermissionService):
    """策略命中应区分 allow 与 deny。"""

    ctx = UserPermissionContext(
        user_id=1,
        role="staff",
        allowed_tables=["fdmdata.*"],
        denied_tables={"fdmdata.t_secret"},
    )

    with patch(
        "app.ai.utils.sql_parser.extract_tables_from_sql",
        return_value={"fdmdata.t_secret", "fdmdata.f_mid_dep_tb"},
    ):
        hits = permission_service.collect_permission_hits_for_sql("SELECT * FROM fdmdata.f_mid_dep_tb", ctx)

    hit_map = {hit.full_name: hit for hit in hits}
    assert hit_map["fdmdata.f_mid_dep_tb"].allowed is True
    assert hit_map["fdmdata.f_mid_dep_tb"].hit_rule_type == "allow"
    assert hit_map["fdmdata.t_secret"].allowed is False
    assert hit_map["fdmdata.t_secret"].hit_rule_type == "deny"


def test_check_table_access_exact_deny_overrides_schema_wildcard_allow(
    permission_service: PermissionService,
):
    """精确 deny 规则应覆盖 schema.* 通配 allow 规则。"""

    ctx = UserPermissionContext(
        user_id=7,
        data_role="staff",
        allowed_tables=["fdmdata.*"],
        denied_tables={"fdmdata.f_mid_loan_k_tb", "fdmdata.f_mid_loan_tb"},
    )

    allowed, reason = permission_service.check_table_access(ctx, "fdmdata", "f_mid_loan_k_tb")
    assert allowed is False
    assert "禁止访问" in str(reason or "")

    allowed_other, reason_other = permission_service.check_table_access(ctx, "fdmdata", "f_mid_dep_tb")
    assert allowed_other is True
    assert reason_other is None


def test_check_table_access_staff_denies_multiple_loan_tables(permission_service: PermissionService):
    """staff 贷款表 deny 应覆盖多个目标表。"""

    ctx = UserPermissionContext(
        user_id=8,
        data_role="staff",
        allowed_tables=["fdmdata.*"],
        denied_tables={"fdmdata.f_mid_loan_k_tb", "fdmdata.f_mid_loan_tb"},
    )

    deny_cases = [("fdmdata", "f_mid_loan_k_tb"), ("fdmdata", "f_mid_loan_tb")]
    for schema, table in deny_cases:
        allowed, reason = permission_service.check_table_access(ctx, schema, table)
        assert allowed is False
        assert f"{schema}.{table}" in str(reason or "")


def test_replace_data_role_policy_rejects_duplicate_rules(permission_service: PermissionService):
    """重复规则应在写库前被拒绝。"""

    db = MagicMock()

    with pytest.raises(ValueError, match="重复规则"):
        permission_service.replace_data_role_policy(
            "staff",
            table_rules=[
                {"schema_name": "fdmdata", "table_name": "f_mid_dep_tb", "allow_access": True},
                {"schema_name": "fdmdata", "table_name": "f_mid_dep_tb", "allow_access": False},
            ],
            row_rules=[],
            column_rules=[],
            db=db,
        )

    db.commit.assert_not_called()


def test_replace_data_role_policy_writes_records_and_invalidate_cache(permission_service: PermissionService):
    """全量替换策略后应提交事务并失效缓存。"""

    db = MagicMock()
    query_obj = MagicMock()
    filtered_obj = MagicMock()
    filtered_obj.delete.return_value = 0
    query_obj.filter.return_value = filtered_obj
    db.query.return_value = query_obj

    with patch.object(permission_service, "invalidate_cache") as mock_invalidate, patch.object(
        permission_service,
        "get_data_role_policy",
        return_value={
            "table_rules": [],
            "row_rules": [],
            "column_rules": [],
            "summary": {
                "table_rule_count": 0,
                "row_rule_count": 0,
                "column_rule_count": 0,
            },
        },
    ):
        permission_service.replace_data_role_policy(
            "staff",
            table_rules=[
                {
                    "schema_name": "fdmdata",
                    "table_name": "f_mid_dep_tb",
                    "allow_access": True,
                    "description": "test",
                }
            ],
            row_rules=[
                {
                    "schema_name": "fdmdata",
                    "table_name": "f_mid_dep_tb",
                    "filter_column": "dept_code",
                    "filter_source": "user.dept_code",
                    "filter_operator": "=",
                }
            ],
            column_rules=[
                {
                    "schema_name": "fdmdata",
                    "table_name": "f_mid_dep_tb",
                    "column_name": "mobile",
                    "mask_type": "partial",
                }
            ],
            db=db,
        )

    db.commit.assert_called_once()
    mock_invalidate.assert_called_once()
    assert db.add_all.call_count == 3

    first_batch = db.add_all.call_args_list[0].args[0]
    second_batch = db.add_all.call_args_list[1].args[0]
    third_batch = db.add_all.call_args_list[2].args[0]

    assert isinstance(first_batch[0], DataPermissionTable)
    assert isinstance(second_batch[0], DataPermissionRow)
    assert isinstance(third_batch[0], DataPermissionColumn)


def test_delete_data_role_policy_returns_deleted_counts(permission_service: PermissionService):
    """删除策略应返回分层删除计数。"""

    db = MagicMock()
    delete_counts = iter([2, 1, 3])

    def _query_side_effect(_model):
        query_obj = MagicMock()
        filtered_obj = MagicMock()
        filtered_obj.delete.return_value = next(delete_counts)
        query_obj.filter.return_value = filtered_obj
        return query_obj

    db.query.side_effect = _query_side_effect

    with patch.object(permission_service, "invalidate_cache") as mock_invalidate:
        result = permission_service.delete_data_role_policy("staff", db)

    assert result["deleted"] == {"table_rules": 2, "row_rules": 1, "column_rules": 3}
    assert result["total_deleted"] == 6
    db.commit.assert_called_once()
    mock_invalidate.assert_called_once()


def test_evaluate_sql_dry_run_returns_reason_and_hits(permission_service: PermissionService):
    """SQL 试跑应携带策略命中轨迹。"""

    ctx = UserPermissionContext(user_id=9, role="department_vgm")
    hit = PermissionHitAudit(
        schema_name="fdmdata",
        table_name="f_mid_dep_tb",
        full_name="fdmdata.f_mid_dep_tb",
        allowed=False,
        hit_rule_type="default_deny",
        matched_rule=None,
        reason="数据角色 department_vgm 无权访问表 fdmdata.f_mid_dep_tb",
    )

    with patch.object(permission_service, "get_user_permission_context", return_value=ctx), patch.object(
        permission_service,
        "collect_permission_hits_for_sql",
        return_value=[hit],
    ), patch(
        "app.ai.utils.sql_policy_decision.evaluate_sql_policy",
        return_value=SqlPolicyDecision(
            is_allowed=False,
            rewritten_sql="SELECT * FROM fdmdata.f_mid_dep_tb",
            reason="数据角色 department_vgm 无权访问表 fdmdata.f_mid_dep_tb",
            reason_code="permission_rejected",
            denied_stage="permission",
        ),
    ):
        result = permission_service.evaluate_sql_dry_run(
            user_id=9,
            sql="SELECT * FROM fdmdata.f_mid_dep_tb",
            db=MagicMock(),
        )

    assert result["user_id"] == 9
    assert result["data_role"] == "department_vgm"
    assert result["is_allowed"] is False
    assert result["reason_code"] == "permission_rejected"
    assert result["denied_stage"] == "permission"
    assert len(result["policy_hits"]) == 1
    assert result["policy_hits"][0]["hit_rule_type"] == "default_deny"


def test_validate_query_context_allows_when_explicit_row_scope_exists_without_dept(
    permission_service: PermissionService,
):
    """缺少 dept_code 但存在显式行级规则时不应触发默认拒绝。"""

    ctx = UserPermissionContext(
        user_id=2,
        data_role="staff",
        org_code="ORG001",
        row_filters={"fdmdata.*": [("org_code", "=", "ORG001")]},
    )

    allowed, reason = permission_service.validate_query_context(ctx)

    assert allowed is True
    assert reason is None


def test_get_row_filters_for_table_skips_default_dept_when_explicit_filter_exists(
    permission_service: PermissionService,
):
    """已有显式行级规则时不再追加默认 dept_code 过滤。"""

    ctx = UserPermissionContext(
        user_id=2,
        data_role="staff",
        dept_code="00808",
        row_filters={"fdmdata.*": [("dept_cd", "=", "00808")]},
    )

    filters = permission_service.get_row_filters_for_table(ctx, "fdmdata", "f_mid_loan_k_tb")

    assert ("dept_cd", "=", "00808") in filters
    assert ("dept_code", "=", "00808") not in filters


def test_get_row_filters_for_table_exact_rule_overrides_schema_wildcard(
    permission_service: PermissionService,
):
    """同表存在精确规则时，应覆盖 schema.* 通配规则。"""

    ctx = UserPermissionContext(
        user_id=4,
        data_role="staff",
        dept_code="00808",
        row_filters={
            "fdmdata.*": [("dept_cd", "=", "00808")],
            "fdmdata.f_mid_index_result": [("org_no", "=", "00808")],
        },
    )

    filters = permission_service.get_row_filters_for_table(ctx, "fdmdata", "f_mid_index_result")

    assert filters == [("org_no", "=", "00808")]


def test_get_row_filters_for_table_appends_default_dept_when_no_explicit_filter(
    permission_service: PermissionService,
):
    """无显式行级规则时仍应追加默认 dept_code 过滤。"""

    ctx = UserPermissionContext(user_id=3, data_role="staff", dept_code="D001")

    filters = permission_service.get_row_filters_for_table(ctx, "fdmdata", "any_table")

    assert filters == [("dept_code", "=", "D001")]


def test_summarize_permission_scope_prefers_org_and_dept_display(
    permission_service: PermissionService,
):
    """权限范围摘要应输出可读机构/部门文案。"""

    ctx = UserPermissionContext(
        user_id=11,
        data_role="staff",
        org_code="440100",
        org_name="广州分行",
        dept_code="A012",
        dept_name="公司金融部",
        row_filters={"fdmdata.*": [("dept_code", "=", "A012")]},
    )

    summary = permission_service.summarize_permission_scope(ctx)

    assert summary["data_role"] == "staff"
    assert summary["org_code"] == "440100"
    assert summary["dept_code"] == "A012"
    assert summary["has_explicit_row_filters"] is True
    assert summary["row_scope_keys"] == ["fdmdata.*"]
    assert summary["display_text"] == "机构：广州分行（440100）；部门：公司金融部（A012）"


def test_summarize_permission_scope_falls_back_to_rule_hint(
    permission_service: PermissionService,
):
    """缺少机构/部门信息时，仍应给出规则级别提示。"""

    ctx = UserPermissionContext(
        user_id=12,
        data_role="staff",
        row_filters={"fdmdata.f_mid_dep_tb": [("org_no", "=", "440100")]},
    )

    summary = permission_service.summarize_permission_scope(ctx)

    assert summary["has_explicit_row_filters"] is True
    assert summary["display_text"] == "已命中预设行级权限规则"


def test_validate_query_context_head_president_with_org_code_rules(
    permission_service: PermissionService,
):
    """head_president 无 dept_code 但有显式 org_code 行级规则时应放行。"""

    ctx = UserPermissionContext(
        user_id=1,
        data_role="head_president",
        sys_role="admin",
        org_code="0000",
        row_filters={"fdmdata.*": [("org_code", "=", "0000")]},
    )

    allowed, reason = permission_service.validate_query_context(ctx)

    assert allowed is True
    assert reason is None


def test_validate_query_context_staff_no_dept_code_still_blocked(
    permission_service: PermissionService,
):
    """staff 无 dept_code 且无显式行级规则时仍应被拒绝。"""

    ctx = UserPermissionContext(
        user_id=2,
        data_role="staff",
    )

    allowed, reason = permission_service.validate_query_context(ctx)

    assert allowed is False
    assert "缺少 dept_code" in reason
    assert "data_role=staff" in reason


def test_get_row_filters_head_president_uses_explicit_org_code_rule(
    permission_service: PermissionService,
):
    """head_president 有显式 org_code 规则时，不注入默认 dept_code 过滤。"""

    ctx = UserPermissionContext(
        user_id=1,
        data_role="head_president",
        org_code="0000",
        row_filters={"fdmdata.*": [("org_code", "=", "0000")]},
    )

    filters = permission_service.get_row_filters_for_table(ctx, "fdmdata", "f_mid_loan_k_tb")

    assert ("org_code", "=", "0000") in filters
    assert all(f[0] != "dept_code" for f in filters)
