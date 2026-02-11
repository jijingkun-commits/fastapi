"""问数图表载荷生成测试（中文注释）。

覆盖场景：
- viz_type=柱状图，客户/金额 -> 生成 bar
- viz_type=折线图，日期/金额 -> 生成 line
- 无数值列 -> 不生成 chart
- 图表请求但空结果 -> 不生成 chart
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

