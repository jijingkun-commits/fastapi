"""问数图表载荷生成测试（中文注释）。

覆盖场景：
- viz_type=柱状图，客户/金额 -> 生成 bar
- viz_type=折线图，日期/金额 -> 生成 line
- 无数值列 -> 不生成 chart
- 图表请求但空结果 -> 不生成 chart
- 维度值重复/为空时 -> 图元仍与行数一致
- 标识列为数字字符串时 -> 不误判为 y 轴指标
- 日期数字列不应被误判为 y 轴指标
- 图表字段语义契约（field_meta）稳定输出
"""
from __future__ import annotations

import importlib
from typing import Any, Dict, List


class _DummyVanna:
    """用于替代 vanna.run_sql 的简易桩对象。"""

    def __init__(self, rows: List[Dict[str, Any]], columns: List[str]):
        self._rows = rows
        self._columns = columns

    def run_sql(self, sql: str):
        _ = sql
        return _DummyDataFrame(self._rows, self._columns)


class _DummyDataFrame:
    """最小 DataFrame 行为桩，满足 sql_execute 依赖。"""

    def __init__(self, rows: List[Dict[str, Any]], columns: List[str]):
        self._rows = rows
        self.columns = columns

    def to_dict(self, orient: str = "records"):
        assert orient == "records"
        return list(self._rows)


def _setup_common_patches(monkeypatch, module, rows: List[Dict[str, Any]], columns: List[str]):
    """统一打桩，隔离外部依赖。"""
    monkeypatch.setattr(module, "get_stream_writer", lambda: (lambda _: None))
    monkeypatch.setattr(module, "emit_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "emit_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "emit_error", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "get_vanna", lambda: _DummyVanna(rows=rows, columns=columns))
    monkeypatch.setattr(module, "_enrich_result_rows_if_needed", lambda result_data, cols: (result_data, cols))
    monkeypatch.setattr(module, "_load_column_display_name_map", lambda cols, sql: {})
    monkeypatch.setattr(module, "_load_column_data_type_map", lambda cols, sql: {})
    monkeypatch.setattr(module, "_build_column_display_names", lambda cols, _: cols)
    monkeypatch.setattr(module, "_build_display_sql", lambda sql, _: sql)
    monkeypatch.setattr(module, "is_effectively_empty_result", lambda data: not data)
    monkeypatch.setattr(module, "rewrite_sql_for_empty_result", lambda sql: (sql, None))
    monkeypatch.setattr(module, "_interpret_result", lambda question, sql, result: "查询完成")


def _extract_chart_from_sql_execute_output(result: Dict[str, Any]) -> Dict[str, Any] | None:
    """提取 sql_execute 返回消息中的 chart 载荷。"""
    messages = result.get("messages") or []
    if not messages:
        return None
    ai_message = messages[0]
    additional_kwargs = getattr(ai_message, "additional_kwargs", {}) or {}
    data = additional_kwargs.get("data") or {}
    if not isinstance(data, dict):
        return None
    chart = data.get("chart")
    return chart if isinstance(chart, dict) else None


def test_sql_execute_builds_bar_chart_for_customer_amount(monkeypatch):
    """viz_type=柱状图 + 客户/金额两列，生成 bar 图表。"""
    module = importlib.import_module("app.ai.workflow.data_graph")

    rows = [
        {"客户名称": "客户A", "贷款金额": 1526000000},
        {"客户名称": "客户B", "贷款金额": 992000000},
        {"客户名称": "客户C", "贷款金额": 692000000},
    ]
    columns = ["客户名称", "贷款金额"]

    _setup_common_patches(monkeypatch, module, rows=rows, columns=columns)

    state = {
        "generated_sql": "SELECT 客户名称, 贷款金额 FROM t_demo",
        "query_context": {"original_question": "查询2025-06-30贷款余额前10名客户"},
        "data_intent": "visualization",
        "viz_type": "柱状图",
        "sql_source": "vanna_rag",
        "iterations": 1,
    }

    output = module.sql_execute(state)
    chart = _extract_chart_from_sql_execute_output(output)

    assert chart is not None
    assert chart["type"] == "bar"
    assert chart["x_key"] == "客户名称"
    assert chart["y_key"] == "贷款金额"
    assert len(chart["data"]) == 3

    field_meta = chart.get("field_meta") or {}
    assert field_meta["客户名称"]["role"] == "dimension"
    assert field_meta["客户名称"]["axis_hint"] == "x"
    assert field_meta["贷款金额"]["role"] == "measure"
    assert field_meta["贷款金额"]["axis_hint"] == "y"


def test_sql_execute_includes_permission_scope_summary_in_message_payload(monkeypatch):
    """权限重写生效时应在 sql_result 中返回范围摘要，并在解释中体现。"""
    module = importlib.import_module("app.ai.workflow.data_graph")

    rows = [{"贷款余额": 100.0}]
    columns = ["贷款余额"]

    _setup_common_patches(monkeypatch, module, rows=rows, columns=columns)

    state = {
        "generated_sql": "SELECT 贷款余额 FROM t_demo",
        "query_context": {
            "original_question": "查询本月贷款余额",
            "permission_rewritten": True,
            "permission_scope_summary": {
                "display_text": "机构：广州分行（440100）；部门：公司金融部（A012）",
            },
        },
        "data_intent": "metric_query",
        "sql_source": "vanna_rag",
        "iterations": 1,
    }

    output = module.sql_execute(state)
    messages = output.get("messages") or []
    assert messages

    ai_message = messages[0]
    text = getattr(ai_message, "content", "")
    assert "机构：广州分行（440100）；部门：公司金融部（A012）" in text

    payload = getattr(ai_message, "additional_kwargs", {}).get("data", {})
    assert payload.get("permission_scope_applied") is True
    assert payload.get("permission_scope_summary", {}).get("display_text") == (
        "机构：广州分行（440100）；部门：公司金融部（A012）"
    )


def test_sql_execute_builds_line_chart_for_date_amount(monkeypatch):
    """viz_type=折线图 + 日期/金额两列，生成 line 图表。"""
    module = importlib.import_module("app.ai.workflow.data_graph")

    rows = [
        {"data_dt": "2025-06-28", "贷款金额": 100.0},
        {"data_dt": "2025-06-29", "贷款金额": 110.5},
        {"data_dt": "2025-06-30", "贷款金额": 120.3},
    ]
    columns = ["data_dt", "贷款金额"]

    _setup_common_patches(monkeypatch, module, rows=rows, columns=columns)

    state = {
        "generated_sql": "SELECT data_dt, 贷款金额 FROM t_demo",
        "query_context": {"original_question": "按日期看贷款余额趋势"},
        "data_intent": "visualization",
        "viz_type": "折线图",
        "sql_source": "vanna_rag",
        "iterations": 1,
    }

    output = module.sql_execute(state)
    chart = _extract_chart_from_sql_execute_output(output)

    assert chart is not None
    assert chart["type"] == "line"
    assert chart["x_key"] == "data_dt"
    assert chart["y_key"] == "贷款金额"
    assert len(chart["data"]) == 3

    field_meta = chart.get("field_meta") or {}
    assert field_meta["data_dt"]["semantic_type"] == "temporal"
    assert field_meta["data_dt"]["axis_hint"] == "x"
    assert field_meta["贷款金额"]["semantic_type"] == "numeric"


def test_sql_execute_skips_chart_when_no_numeric_column(monkeypatch):
    """无数值列时，chart 应为空（仅保留表格）。"""
    module = importlib.import_module("app.ai.workflow.data_graph")

    rows = [
        {"客户名称": "客户A", "地区": "杭州"},
        {"客户名称": "客户B", "地区": "嘉兴"},
    ]
    columns = ["客户名称", "地区"]

    _setup_common_patches(monkeypatch, module, rows=rows, columns=columns)

    state = {
        "generated_sql": "SELECT 客户名称, 地区 FROM t_demo",
        "query_context": {"original_question": "以柱状图看客户分布"},
        "data_intent": "visualization",
        "viz_type": "柱状图",
        "sql_source": "vanna_rag",
        "iterations": 1,
    }

    output = module.sql_execute(state)
    chart = _extract_chart_from_sql_execute_output(output)

    assert chart is None


def test_sql_execute_skips_chart_when_result_empty(monkeypatch):
    """图表请求但查询为空结果时，不生成 chart。"""
    module = importlib.import_module("app.ai.workflow.data_graph")

    rows: List[Dict[str, Any]] = []
    columns = ["客户名称", "贷款金额"]

    _setup_common_patches(monkeypatch, module, rows=rows, columns=columns)

    state = {
        "generated_sql": "SELECT 客户名称, 贷款金额 FROM t_demo",
        "query_context": {"original_question": "以柱状图看Top10贷款余额"},
        "data_intent": "visualization",
        "viz_type": "柱状图",
        "sql_source": "vanna_rag",
        "iterations": 1,
    }

    output = module.sql_execute(state)
    chart = _extract_chart_from_sql_execute_output(output)

    assert chart is None


def test_sql_execute_keeps_unique_points_when_dimension_has_duplicates(monkeypatch):
    """维度列含重复/空值时，图表应保留逐行可区分的图元。"""
    module = importlib.import_module("app.ai.workflow.data_graph")

    rows = [
        {"ecif_cust_no": "2009001293", "客户名称": None, "贷款金额": 15.26 * 1_0000_0000},
        {"ecif_cust_no": "2110009159", "客户名称": "潮州华盛物流贸易有限公司", "贷款金额": 9.92 * 1_0000_0000},
        {"ecif_cust_no": "2000045474", "客户名称": None, "贷款金额": 6.92 * 1_0000_0000},
        {"ecif_cust_no": "2110019805", "客户名称": "兰钧新能源科技有限公司-保证金", "贷款金额": 6.12 * 1_0000_0000},
    ]
    columns = ["ecif_cust_no", "客户名称", "贷款金额"]

    _setup_common_patches(monkeypatch, module, rows=rows, columns=columns)

    state = {
        "generated_sql": "SELECT ecif_cust_no, 客户名称, 贷款金额 FROM t_demo",
        "query_context": {"original_question": "查询2025-06-30贷款余额前10名客户"},
        "data_intent": "visualization",
        "viz_type": "柱状图",
        "sql_source": "vanna_rag",
        "iterations": 1,
    }

    output = module.sql_execute(state)
    chart = _extract_chart_from_sql_execute_output(output)

    assert chart is not None
    assert len(chart["data"]) == 4

    x_values = [item[chart["x_key"]] for item in chart["data"]]
    assert len(set(x_values)) == 4
    assert any(str(value).startswith("未知（2009001293") for value in x_values)
    assert any(str(value).startswith("未知（2000045474") for value in x_values)


def test_pick_chart_axes_keeps_identifier_column_as_dimension():
    """标识列即使全为数字字符串，也不应被当作 y 轴指标。"""
    module = importlib.import_module("app.ai.workflow.data_graph")

    rows = [
        {"客户编号": "1001", "value": 10.0},
        {"客户编号": "1002", "value": 20.0},
        {"客户编号": "1003", "value": 30.0},
    ]
    columns = ["客户编号", "value"]

    x_key, y_key = module._pick_chart_axes(columns, rows)
    assert x_key == "客户编号"
    assert y_key == "value"


def test_pick_chart_axes_avoids_date_like_numeric_column_as_measure():
    """YYYYMMDD 数字日期列不应被选为 y 轴度量。"""
    module = importlib.import_module("app.ai.workflow.data_graph")

    rows = [
        {"业务日期": 20250630, "机构号": "CF001", "年日均余额": 2375.35},
        {"业务日期": 20250630, "机构号": "CF002", "年日均余额": 7183.53},
        {"业务日期": 20250630, "机构号": "CF003", "年日均余额": 4594.55},
    ]
    columns = ["业务日期", "机构号", "年日均余额"]

    x_key, y_key = module._pick_chart_axes(columns, rows)
    assert x_key == "机构号"
    assert y_key == "年日均余额"


def test_sql_execute_outputs_field_meta_for_temporal_guardrail(monkeypatch):
    """固定单日场景输出 field_meta，且日期列不进入 y 轴。"""
    module = importlib.import_module("app.ai.workflow.data_graph")

    rows = [
        {"业务日期": 20250630, "机构号": "CF001", "年日均余额": 2375.35},
        {"业务日期": 20250630, "机构号": "CF002", "年日均余额": 7183.53},
        {"业务日期": 20250630, "机构号": "CF003", "年日均余额": 4594.55},
    ]
    columns = ["业务日期", "机构号", "年日均余额"]

    _setup_common_patches(monkeypatch, module, rows=rows, columns=columns)

    state = {
        "generated_sql": "SELECT 业务日期, 机构号, 年日均余额 FROM t_demo",
        "query_context": {"original_question": "2025-06-30按机构看年日均余额"},
        "data_intent": "visualization",
        "viz_type": "柱状图",
        "sql_source": "vanna_rag",
        "iterations": 1,
    }

    output = module.sql_execute(state)
    chart = _extract_chart_from_sql_execute_output(output)

    assert chart is not None
    assert chart["x_key"] == "机构号"
    assert chart["y_key"] == "年日均余额"

    field_meta = chart.get("field_meta") or {}
    assert field_meta["业务日期"]["role"] == "time"
    assert field_meta["业务日期"]["semantic_type"] == "temporal"
    assert field_meta["业务日期"]["axis_hint"] == "none"
    assert field_meta["年日均余额"]["role"] == "measure"
    assert field_meta["年日均余额"]["axis_hint"] == "y"


def test_pick_chart_axes_prefers_multi_point_date_dimension_for_trend():
    """存在多日期点时，日期维度可作为 x 轴（趋势语义）。"""
    module = importlib.import_module("app.ai.workflow.data_graph")

    rows = [
        {"业务日期": 20250628, "贷款余额": 100.0},
        {"业务日期": 20250629, "贷款余额": 110.0},
        {"业务日期": 20250630, "贷款余额": 120.0},
    ]
    columns = ["业务日期", "贷款余额"]

    x_key, y_key = module._pick_chart_axes(columns, rows)
    assert x_key == "业务日期"
    assert y_key == "贷款余额"
