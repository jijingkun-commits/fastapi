"""访问控制管理 API 测试（中文注释）。"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]


# 通过预注册轻量包，避免触发各目录 __init__ 的重依赖导入。
def _register_lightweight_package(module_name: str, relative_path: str):
    if module_name in sys.modules:
        return
    pkg = types.ModuleType(module_name)
    pkg.__path__ = [str(ROOT_DIR / relative_path)]
    sys.modules[module_name] = pkg


_register_lightweight_package("app.models", "app/models")
_register_lightweight_package("app.services", "app/services")
_register_lightweight_package("app.ai.utils", "app/ai/utils")

# 避免导入 app.ai.semantic.__init__ 时拉起重依赖（pandas/vanna）。
_fake_semantic_pkg = types.ModuleType("app.ai.semantic")
_fake_semantic_pkg.__path__ = []
_fake_dac_module = types.ModuleType("app.ai.semantic.data_access_control")


class _FakeDataAccessControl:
    def extract_tables_from_sql(self, _sql: str):
        return []

    def check_table_access(self, _table: str) -> bool:
        return True


_fake_dac_module.DataAccessControl = _FakeDataAccessControl
_fake_dac_module.DEFAULT_TABLE_WHITELIST = {"t_orders"}
_fake_dac_module.DEFAULT_TABLE_BLACKLIST = {"t_user"}
_fake_dac_module.DEFAULT_SCHEMA_BLACKLIST = {"pg_catalog", "information_schema"}
_fake_dac_module.invalidate_config_cache = lambda: None

sys.modules.setdefault("app.ai.semantic", _fake_semantic_pkg)
sys.modules.setdefault("app.ai.semantic.data_access_control", _fake_dac_module)

from app.api.deps import get_admin_user
from app.api.v1.endpoints import access_admin_api
from app.db.session import get_db


@pytest.fixture()
def admin_client():
    """提供带管理员与数据库覆盖的测试客户端。"""

    app = FastAPI()
    fake_db = MagicMock()

    app.include_router(
        access_admin_api.router,
        prefix="/api/v1",
        dependencies=[Depends(get_admin_user)],
    )

    app.dependency_overrides[get_admin_user] = lambda: SimpleNamespace(
        id=1,
        role="admin",
        is_active=True,
    )

    def _override_db():
        yield fake_db

    app.dependency_overrides[get_db] = _override_db

    with TestClient(app) as client:
        yield client, fake_db

    app.dependency_overrides.clear()


def _build_policy_payload() -> dict:
    """构造最小可用策略响应。"""

    return {
        "table_rules": [
            {
                "schema_name": "fdmdata",
                "table_name": "f_mid_dep_tb",
                "allow_access": True,
                "description": "存款明细可查",
            }
        ],
        "row_rules": [
            {
                "schema_name": "fdmdata",
                "table_name": "f_mid_dep_tb",
                "filter_column": "dept_code",
                "filter_source": "user.dept_code",
                "filter_value": None,
                "filter_operator": "=",
                "description": "默认部门隔离",
            }
        ],
        "column_rules": [
            {
                "schema_name": "fdmdata",
                "table_name": "f_mid_dep_tb",
                "column_name": "mobile",
                "mask_type": "partial",
                "description": "手机号脱敏",
            }
        ],
        "summary": {
            "table_rule_count": 1,
            "row_rule_count": 1,
            "column_rule_count": 1,
        },
    }


def test_data_role_policy_requires_admin_auth():
    """未携带管理员认证时应拒绝访问。"""

    app = FastAPI()
    app.include_router(
        access_admin_api.router,
        prefix="/api/v1",
        dependencies=[Depends(get_admin_user)],
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/access-admin/data-roles")

    assert response.status_code in [401, 403, 422]


def test_list_data_role_policies_success(admin_client):
    """应返回四个冻结 data_role 的策略摘要。"""

    client, _ = admin_client

    service_stub = MagicMock()
    service_stub.get_data_role_policy.side_effect = [
        _build_policy_payload(),
        _build_policy_payload(),
        _build_policy_payload(),
        _build_policy_payload(),
    ]

    with patch(
        "app.api.v1.endpoints.access_admin_api.get_permission_service",
        return_value=service_stub,
    ):
        response = client.get("/api/v1/access-admin/data-roles")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 4
    assert data["items"][0]["data_role"] == "head_president"
    assert data["items"][3]["data_role"] == "staff"


def test_update_data_role_policy_success(admin_client):
    """更新 data_role 策略应透传到权限服务。"""

    client, fake_db = admin_client

    service_stub = MagicMock()
    service_stub.replace_data_role_policy.return_value = _build_policy_payload()

    payload = {
        "table_rules": [
            {
                "schema_name": "FDMDATA",
                "table_name": "F_MID_DEP_TB",
                "allow_access": True,
                "description": "test",
            }
        ],
        "row_rules": [
            {
                "schema_name": "fdmdata",
                "table_name": "f_mid_dep_tb",
                "filter_column": "DEPT_CODE",
                "filter_source": "user.dept_code",
                "filter_operator": "=",
                "description": "test",
            }
        ],
        "column_rules": [
            {
                "schema_name": "fdmdata",
                "table_name": "f_mid_dep_tb",
                "column_name": "MOBILE",
                "mask_type": "partial",
                "description": "test",
            }
        ],
    }

    with patch(
        "app.api.v1.endpoints.access_admin_api.get_permission_service",
        return_value=service_stub,
    ):
        response = client.put("/api/v1/access-admin/data-roles/staff", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["data_role"] == "staff"
    assert body["summary"]["table_rule_count"] == 1

    kwargs = service_stub.replace_data_role_policy.call_args.kwargs
    assert kwargs["db"] is fake_db
    assert kwargs["table_rules"][0]["schema_name"] == "fdmdata"
    assert kwargs["row_rules"][0]["filter_column"] == "dept_code"
    assert kwargs["column_rules"][0]["column_name"] == "mobile"


def test_update_data_role_policy_with_invalid_payload_returns_400(admin_client):
    """服务层校验失败时接口应返回 400。"""

    client, _ = admin_client

    service_stub = MagicMock()
    service_stub.replace_data_role_policy.side_effect = ValueError("table_rules 存在重复规则")

    payload = {
        "table_rules": [
            {
                "schema_name": "fdmdata",
                "table_name": "f_mid_dep_tb",
                "allow_access": True,
            }
        ],
        "row_rules": [],
        "column_rules": [],
    }

    with patch(
        "app.api.v1.endpoints.access_admin_api.get_permission_service",
        return_value=service_stub,
    ):
        response = client.put("/api/v1/access-admin/data-roles/staff", json=payload)

    assert response.status_code == 400
    assert "重复规则" in response.json()["detail"]


def test_delete_data_role_policy_success(admin_client):
    """删除 data_role 策略应返回删除计数。"""

    client, _ = admin_client

    service_stub = MagicMock()
    service_stub.delete_data_role_policy.return_value = {
        "deleted": {"table_rules": 2, "row_rules": 1, "column_rules": 3},
        "total_deleted": 6,
    }

    with patch(
        "app.api.v1.endpoints.access_admin_api.get_permission_service",
        return_value=service_stub,
    ):
        response = client.delete("/api/v1/access-admin/data-roles/department_gm")

    assert response.status_code == 200
    data = response.json()
    assert data["data_role"] == "department_gm"
    assert data["total_deleted"] == 6


def test_sql_dry_run_returns_policy_hits(admin_client):
    """SQL 试跑接口应返回重写结果与策略命中。"""

    client, _ = admin_client

    service_stub = MagicMock()
    service_stub.evaluate_sql_dry_run.return_value = {
        "user_id": 9,
        "data_role": "staff",
        "is_allowed": False,
        "original_sql": "SELECT * FROM fdmdata.f_mid_dep_tb",
        "rewritten_sql": "SELECT * FROM fdmdata.f_mid_dep_tb",
        "reason": "数据角色 staff 无权访问表 fdmdata.f_mid_dep_tb",
        "reason_code": "permission_rejected",
        "denied_stage": "permission",
        "policy_hits": [
            {
                "schema_name": "fdmdata",
                "table_name": "f_mid_dep_tb",
                "full_name": "fdmdata.f_mid_dep_tb",
                "allowed": False,
                "hit_rule_type": "default_deny",
                "matched_rule": None,
                "reason": "数据角色 staff 无权访问表 fdmdata.f_mid_dep_tb",
            }
        ],
    }

    payload = {
        "user_id": 9,
        "sql": "SELECT * FROM fdmdata.f_mid_dep_tb",
        "auto_limit": True,
        "limit": 500,
    }

    with patch(
        "app.api.v1.endpoints.access_admin_api.get_permission_service",
        return_value=service_stub,
    ):
        response = client.post("/api/v1/access-admin/sql-dry-run", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["is_allowed"] is False
    assert data["reason_code"] == "permission_rejected"
    assert data["policy_hits"][0]["hit_rule_type"] == "default_deny"
