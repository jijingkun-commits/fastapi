"""askdata/data_access 配置键兼容回归测试。"""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.ai.semantic import data_access_control
from app.api.v1.endpoints import access_admin_api


@contextmanager
def _fake_db_context():
    """提供一个最小可用的假数据库上下文。"""

    yield object()


def _build_db_mock(first_side_effect):
    """构建支持 query().filter().first() 链式调用的 mock。"""

    db = MagicMock()
    query_obj = MagicMock()
    filter_obj = MagicMock()
    filter_obj.first.side_effect = first_side_effect
    query_obj.filter.return_value = filter_obj
    db.query.return_value = query_obj
    return db, filter_obj


def setup_function():
    """每个测试前清理缓存，避免互相污染。"""

    data_access_control.invalidate_config_cache()


def teardown_function():
    """每个测试后清理缓存，避免影响其他测试。"""

    data_access_control.invalidate_config_cache()


@patch("app.repositories.config_repo.get_config_value")
def test_load_config_fallback_to_legacy_key(mock_get_config_value, monkeypatch):
    """主键缺失时应回退读取历史键。"""

    monkeypatch.setattr(data_access_control, "get_db_context", _fake_db_context)
    mock_get_config_value.side_effect = [None, "t_orders,t_products"]

    result = data_access_control._load_config_from_db(
        data_access_control.ASKDATA_TABLE_WHITELIST_KEY,
        {"default_table"},
        aliases=(data_access_control.ASKDATA_TABLE_WHITELIST_LEGACY_KEY,),
    )

    assert result == {"t_orders", "t_products"}
    assert mock_get_config_value.call_count == 2


@patch("app.repositories.config_repo.get_config_value")
def test_load_config_prefers_primary_key(mock_get_config_value, monkeypatch):
    """主键存在时应优先使用主键，不继续查历史键。"""

    monkeypatch.setattr(data_access_control, "get_db_context", _fake_db_context)
    mock_get_config_value.side_effect = ["t_orders"]

    result = data_access_control._load_config_from_db(
        data_access_control.ASKDATA_TABLE_WHITELIST_KEY,
        {"default_table"},
        aliases=(data_access_control.ASKDATA_TABLE_WHITELIST_LEGACY_KEY,),
    )

    assert result == {"t_orders"}
    assert mock_get_config_value.call_count == 1


def test_get_config_value_reads_legacy_when_primary_missing():
    """后台读取应兼容历史键。"""

    legacy_config = SimpleNamespace(config_value="t_orders")
    db, filter_obj = _build_db_mock([None, legacy_config])

    value = access_admin_api._get_config_value(db, access_admin_api.CONFIG_KEY_WHITELIST)

    assert value == "t_orders"
    assert filter_obj.first.call_count == 2


def test_get_config_value_schema_reads_askdata_legacy_key_first():
    """schema 配置主键缺失时应先兼容 askdata.schema_whitelist。"""

    legacy_config = SimpleNamespace(config_value="pg_catalog,information_schema")
    db, filter_obj = _build_db_mock([None, legacy_config])

    value = access_admin_api._get_config_value(db, access_admin_api.CONFIG_KEY_SCHEMA_WHITELIST)

    assert value == "pg_catalog,information_schema"
    assert filter_obj.first.call_count == 2


@patch("app.repositories.config_repo.get_config_value")
def test_load_schema_blacklist_fallback_to_askdata_schema_whitelist(
    mock_get_config_value, monkeypatch
):
    """问数访问控制应兼容 askdata.schema_whitelist 历史键。"""

    monkeypatch.setattr(data_access_control, "get_db_context", _fake_db_context)
    mock_get_config_value.side_effect = [None, "pg_catalog,information_schema"]

    result = data_access_control._load_config_from_db(
        data_access_control.ASKDATA_SCHEMA_BLACKLIST_KEY,
        {"default_schema"},
        aliases=data_access_control.ASKDATA_SCHEMA_BLACKLIST_LEGACY_KEYS,
    )

    assert result == {"pg_catalog", "information_schema"}
    assert mock_get_config_value.call_count == 2


def test_set_config_value_writes_primary_key_only_and_invalidate_cache():
    """后台写入只更新 askdata 主键，并触发缓存失效。"""

    db, _ = _build_db_mock([None])

    with patch(
        "app.api.v1.endpoints.access_admin_api.invalidate_config_cache"
    ) as mock_invalidate:
        access_admin_api._set_config_value(
            db,
            access_admin_api.CONFIG_KEY_WHITELIST,
            "t_orders",
            "数据访问控制-表白名单",
        )

    db.commit.assert_called_once()
    db.add.assert_called_once()
    created = db.add.call_args.args[0]
    assert created.config_key == access_admin_api.CONFIG_KEY_WHITELIST
    assert created.category == "askdata"
    mock_invalidate.assert_called_once()


def test_set_config_value_updates_existing_record_without_create():
    """主键已存在时应直接更新，不重复创建记录。"""

    existing_config = SimpleNamespace(config_key="askdata.table_blacklist", config_value="old")
    db, _ = _build_db_mock([existing_config])

    with patch("app.api.v1.endpoints.access_admin_api.invalidate_config_cache"):
        access_admin_api._set_config_value(
            db,
            access_admin_api.CONFIG_KEY_BLACKLIST,
            "t_user,t_chat_message",
            "数据访问控制-表黑名单",
        )

    assert existing_config.config_value == "t_user,t_chat_message"
    db.add.assert_not_called()
    db.commit.assert_called_once()


def test_schema_whitelist_endpoint_maps_to_schema_blacklist_key():
    """历史 schema-whitelist 接口应写入 askdata.schema_blacklist。"""

    request = access_admin_api.UpdateSchemaWhitelistRequest(
        schemas=["pg_catalog", "information_schema"]
    )
    db = MagicMock()

    with patch("app.api.v1.endpoints.access_admin_api._set_config_value") as mock_set_config:
        resp = access_admin_api.update_schema_whitelist(request, db)

    mock_set_config.assert_called_once()
    _, key, stored_value, _ = mock_set_config.call_args.args
    assert key == access_admin_api.CONFIG_KEY_SCHEMA_WHITELIST
    assert stored_value == "information_schema,pg_catalog"
    assert resp["schemas"] == ["information_schema", "pg_catalog"]
