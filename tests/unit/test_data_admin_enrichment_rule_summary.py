"""结果增强规则测试摘要文案单元测试。"""

from app.api.v1.endpoints.data_admin_api import _build_rule_test_summary_message


def test_build_rule_test_summary_message_when_hit_without_data():
    message = _build_rule_test_summary_message(
        matched_rule_codes=["customer_name"],
        applied_rule_codes=[],
        no_data_rule_codes=["customer_name"],
    )

    assert message == "命中规则，但未查询到数据"


def test_build_rule_test_summary_message_when_applied_and_partial_no_data():
    message = _build_rule_test_summary_message(
        matched_rule_codes=["r1", "r2"],
        applied_rule_codes=["r1"],
        no_data_rule_codes=["r2"],
    )

    assert message == "命中 2 条规则，补齐成功 1 条，1 条未查询到数据"


def test_build_rule_test_summary_message_when_no_rule_matched():
    message = _build_rule_test_summary_message(
        matched_rule_codes=[],
        applied_rule_codes=[],
        no_data_rule_codes=[],
    )

    assert message == "未命中规则"
