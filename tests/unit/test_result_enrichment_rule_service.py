"""结果增强规则服务单元测试。"""

from datetime import datetime, timedelta
from unittest.mock import patch

from app.services.result_enrichment_rule_service import (
    ResultEnrichmentRuleService,
    ResultLookupEnrichmentRuleConfig,
    apply_lookup_enrichment_rule,
    apply_lookup_enrichment_rule_with_status,
)


def _build_rule(name: str = "customer_name") -> ResultLookupEnrichmentRuleConfig:
    return ResultLookupEnrichmentRuleConfig(
        name=name,
        key_column_candidates=("ecif_cust_no",),
        target_column="客户名称",
        source_table="fdmdata.f_mid_dep_tb",
        source_key_column="ecif_cust_no",
        source_value_column="cust_acct_name",
        source_date_column="data_dt",
        result_date_column_candidates=("data_dt",),
    )


def test_get_active_rules_ttl_hit_uses_cache():
    service = ResultEnrichmentRuleService(ttl_seconds=120)
    load_count = {"value": 0}
    rule = _build_rule()

    def _load_rules():
        load_count["value"] += 1
        return (rule,)

    with patch.object(service, "_load_active_rules_from_db", side_effect=_load_rules):
        first = service.get_active_rules(fallback_rules=())
        second = service.get_active_rules(fallback_rules=())

    assert first == (rule,)
    assert second == (rule,)
    assert load_count["value"] == 1


def test_get_active_rules_ttl_expired_refreshes_again():
    service = ResultEnrichmentRuleService(ttl_seconds=1)
    load_count = {"value": 0}
    rule = _build_rule()

    def _load_rules():
        load_count["value"] += 1
        return (rule,)

    with patch.object(service, "_load_active_rules_from_db", side_effect=_load_rules):
        service.get_active_rules(fallback_rules=())
        service._cached_at = datetime.now() - timedelta(seconds=5)
        service.get_active_rules(fallback_rules=())

    assert load_count["value"] == 2


def test_get_active_rules_refresh_failure_uses_stale_cache():
    service = ResultEnrichmentRuleService(ttl_seconds=120)
    stale_rule = _build_rule("stale_rule")
    service._cached_rules = (stale_rule,)
    service._cached_at = datetime.now() - timedelta(seconds=1000)

    with patch.object(service, "refresh_rules", side_effect=RuntimeError("db error")):
        result = service.get_active_rules(force_refresh=True, fallback_rules=())

    assert result == (stale_rule,)


def test_get_active_rules_without_cache_fallback_to_default_rules():
    service = ResultEnrichmentRuleService(ttl_seconds=120)
    fallback_rule = _build_rule("fallback_rule")

    with patch.object(service, "refresh_rules", side_effect=RuntimeError("db error")):
        result = service.get_active_rules(force_refresh=True, fallback_rules=(fallback_rule,))

    assert result == (fallback_rule,)


def test_validate_rule_payload_rejects_illegal_source_table():
    service = ResultEnrichmentRuleService(ttl_seconds=120)
    payload = {
        "rule_code": "customer_name",
        "rule_name": "客户名称补齐",
        "enabled": True,
        "priority": 10,
        "key_column_candidates": ["ecif_cust_no"],
        "target_column": "客户名称",
        "source_table": "fdmdata.f_mid_dep_tb;drop table x",
        "source_key_column": "ecif_cust_no",
        "source_value_column": "cust_acct_name",
        "source_date_column": "data_dt",
        "result_date_column_candidates": ["data_dt"],
        "description": "test",
    }

    try:
        service.validate_rule_payload(payload)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "source_table" in str(exc)


def test_validate_rule_payload_normalizes_values():
    service = ResultEnrichmentRuleService(ttl_seconds=120)
    payload = {
        "rule_code": "customer_name",
        "rule_name": "客户名称补齐",
        "enabled": True,
        "priority": "10",
        "key_column_candidates": ["ecif_cust_no", "ecif_cust_no"],
        "target_column": "客户名称",
        "source_table": "fdmdata.f_mid_dep_tb",
        "source_key_column": "ecif_cust_no",
        "source_value_column": "cust_acct_name",
        "source_date_column": "data_dt",
        "result_date_column_candidates": ["data_dt", "data_dt"],
        "description": " test ",
    }

    normalized = service.validate_rule_payload(payload)

    assert normalized["priority"] == 10
    assert normalized["key_column_candidates"] == ["ecif_cust_no"]
    assert normalized["result_date_column_candidates"] == ["data_dt"]
    assert normalized["source_table"] == "fdmdata.f_mid_dep_tb"


def test_apply_lookup_enrichment_rule_inserts_target_column_after_key():
    rule = _build_rule("customer_name")
    rows = [
        {"ecif_cust_no": "1001", "贷款余额": 88.0, "data_dt": "2025-06-30"},
        {"ecif_cust_no": "1002", "贷款余额": 66.0, "data_dt": "2025-06-30"},
    ]
    columns = ["ecif_cust_no", "贷款余额", "data_dt"]

    with patch(
        "app.services.result_enrichment_rule_service._fetch_lookup_value_map",
        return_value={"1001": "张三", "1002": "李四"},
    ):
        new_rows, new_columns = apply_lookup_enrichment_rule(rows, columns, rule)

    assert new_columns == ["ecif_cust_no", "客户名称", "贷款余额", "data_dt"]
    assert new_rows[0]["客户名称"] == "张三"
    assert new_rows[1]["客户名称"] == "李四"


def test_apply_lookup_enrichment_rule_returns_original_when_target_exists():
    rule = _build_rule("customer_name")
    rows = [{"ecif_cust_no": "1001", "客户名称": "张三", "贷款余额": 88.0}]
    columns = ["ecif_cust_no", "客户名称", "贷款余额"]

    with patch(
        "app.services.result_enrichment_rule_service._fetch_lookup_value_map",
        side_effect=AssertionError("不应触发查表"),
    ):
        new_rows, new_columns = apply_lookup_enrichment_rule(rows, columns, rule)

    assert new_rows == rows
    assert new_columns == columns


def test_apply_lookup_enrichment_rule_with_status_marks_no_data_when_lookup_empty():
    rule = _build_rule("customer_name")
    rows = [{"ecif_cust_no": "1001", "贷款余额": 88.0, "data_dt": "2025-06-30"}]
    columns = ["ecif_cust_no", "贷款余额", "data_dt"]

    with patch(
        "app.services.result_enrichment_rule_service._fetch_lookup_value_map",
        return_value={},
    ):
        new_rows, new_columns, status = apply_lookup_enrichment_rule_with_status(rows, columns, rule)

    assert new_rows == rows
    assert new_columns == columns
    assert status.matched is True
    assert status.enriched is False
    assert status.no_data is True
    assert status.reason == "lookup_no_data"


def test_apply_lookup_enrichment_rule_with_status_marks_unmatched_when_key_column_missing():
    rule = _build_rule("customer_name")
    rows = [{"cust_no": "1001", "贷款余额": 88.0}]
    columns = ["cust_no", "贷款余额"]

    with patch(
        "app.services.result_enrichment_rule_service._fetch_lookup_value_map",
        side_effect=AssertionError("不应触发查表"),
    ):
        new_rows, new_columns, status = apply_lookup_enrichment_rule_with_status(rows, columns, rule)

    assert new_rows == rows
    assert new_columns == columns
    assert status.matched is False
    assert status.enriched is False
    assert status.no_data is False
    assert status.reason == "missing_key_column"
