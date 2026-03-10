"""问数 SQL 候选语义护栏单元测试。"""

import json
import unittest
from unittest.mock import patch

from langchain_core.messages import HumanMessage

from app.services.result_enrichment_rule_service import ResultLookupEnrichmentRuleConfig

from app.ai.workflow.data_graph import (
    analyze_data_intent,
    _build_column_display_names,
    _build_display_sql,
    _build_sql_result_additional_kwargs,
    _build_sql_result_chart_payload,
    _coerce_chart_number,
    _derive_metric_sql,
    _enrich_result_rows_if_needed,
    _extract_top_n,
    _is_sql_semantically_compatible,
    _load_column_display_name_map,
    _pick_chart_axes,
    _resolve_sql_empty_result_fallback_policy,
    _requires_detail_query,
    metric_resolve,
    route_after_execute,
)


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class _FakeLLM:
    def __init__(self, payload: dict):
        self.payload = payload

    def invoke(self, _prompt: str):
        return _FakeResponse(json.dumps(self.payload, ensure_ascii=False))


class TestDataGraphSemanticGuard(unittest.TestCase):
    """验证模板/训练 SQL 与用户问题语义一致性。"""

    def test_requires_detail_query_with_dimension(self):
        question = "查询2025年6月30日贷款余额前10名的客户"
        self.assertTrue(_requires_detail_query(question, ["客户"]))

    def test_requires_detail_query_with_topn_keyword_only(self):
        question = "贷款余额前10名"
        self.assertTrue(_requires_detail_query(question, []))

    def test_total_aggregate_sql_rejected_for_topn(self):
        question = "查询2025年6月30日贷款余额前10名的客户"
        sql = """
        SELECT SUM(prin_bal) AS 贷款余额
        FROM fdmdata.f_mid_loan_k_tb
        WHERE data_dt = '20250630'
        """
        self.assertFalse(_is_sql_semantically_compatible(sql, question, ["客户"]))

    def test_topn_sql_accepted_for_topn_question(self):
        question = "查询2025年6月30日贷款余额前10名的客户"
        sql = """
        SELECT cust_no, SUM(prin_bal) AS loan_balance
        FROM fdmdata.f_mid_loan_k_tb
        WHERE data_dt = '20250630'
        GROUP BY cust_no
        ORDER BY loan_balance DESC
        LIMIT 10
        """
        self.assertTrue(_is_sql_semantically_compatible(sql, question, ["客户"]))

    def test_total_question_allows_total_aggregate_sql(self):
        question = "查询2025年6月30日的贷款余额"
        sql = """
        SELECT SUM(prin_bal) AS 贷款余额
        FROM fdmdata.f_mid_loan_k_tb
        WHERE data_dt = '20250630'
        """
        self.assertTrue(_is_sql_semantically_compatible(sql, question, []))

    def test_extract_top_n_default_and_explicit(self):
        self.assertEqual(_extract_top_n("贷款余额前10名客户"), 10)
        self.assertEqual(_extract_top_n("贷款余额top25客户"), 25)
        self.assertEqual(_extract_top_n("贷款余额客户排名"), 10)

    def test_build_sql_result_additional_kwargs_uses_shared_payload_schema(self):
        additional_kwargs = _build_sql_result_additional_kwargs(
            sql="SELECT org_nm, loan_bal FROM fdmdata.f_mid_loan_tb LIMIT 100",
            display_sql="SELECT 机构名称, 贷款余额 FROM fdmdata.f_mid_loan_tb LIMIT 100",
            columns=["org_nm", "loan_bal"],
            column_display_names=["机构名称", "贷款余额"],
            result_data=[
                {"org_nm": "嘉兴分行", "loan_bal": 1526000000.0},
                {"org_nm": "绍兴分行", "loan_bal": 692000000.0},
            ],
            sql_source="metric",
            iterations=1,
            chart_payload={"type": "bar"},
            permission_rewritten=True,
            permission_scope_summary={"display_text": "浙江省分行"},
        )

        self.assertEqual(additional_kwargs.get("data_type"), "sql_result")
        data = additional_kwargs.get("data")
        assert isinstance(data, dict)
        self.assertEqual(data.get("total_rows"), 2)
        self.assertEqual(data.get("sql_source"), "metric")
        self.assertEqual(data.get("iterations"), 1)
        self.assertEqual(data.get("permission_scope_applied"), True)
        self.assertEqual(data.get("permission_scope_summary"), {"display_text": "浙江省分行"})
        self.assertEqual(data.get("rows"), [
            {"org_nm": "嘉兴分行", "loan_bal": 1526000000.0},
            {"org_nm": "绍兴分行", "loan_bal": 692000000.0},
        ])

    def test_resolve_sql_empty_result_fallback_policy(self):
        self.assertEqual(
            _resolve_sql_empty_result_fallback_policy("metric"),
            ("training", "指标模板未查到数据，正在尝试训练集SQL..."),
        )
        self.assertEqual(
            _resolve_sql_empty_result_fallback_policy("training"),
            ("schema", "训练集SQL未查到数据，正在尝试通过表结构生成查询..."),
        )
        self.assertIsNone(_resolve_sql_empty_result_fallback_policy("unknown"))

    def test_route_after_execute_routes_by_fallback_map(self):
        self.assertEqual(route_after_execute({"fallback_target": "training"}), "fallback_training")
        self.assertEqual(route_after_execute({"fallback_target": "schema"}), "fallback_schema")

    def test_coerce_chart_number_supports_chinese_units(self):
        self.assertEqual(_coerce_chart_number("15.26亿"), 1526000000.0)
        self.assertEqual(_coerce_chart_number("15.26 亿"), 1526000000.0)
        self.assertEqual(_coerce_chart_number("6.92万"), 69200.0)

    @patch("app.ai.workflow.data_graph._load_column_data_type_map", return_value={})
    def test_build_chart_payload_prefers_amount_with_unit_strings(self, _mock_type_map):
        state = {"viz_type": "柱状图", "data_intent": "visualization"}
        question = "查询2025年6月30日贷款余额前10名的客户"
        sql = (
            "SELECT ecif_cust_no AS 客户统一编号, cust_name AS 客户名称, loan_bal AS 贷款余额 "
            "FROM fdmdata.f_mid_loan_tb LIMIT 10"
        )
        columns = ["客户统一编号", "客户名称", "贷款余额"]
        rows = [
            {"客户统一编号": "2009001293", "客户名称": None, "贷款余额": "15.26 亿"},
            {"客户统一编号": "2000045474", "客户名称": None, "贷款余额": "6.92 亿"},
            {"客户统一编号": "2000068157", "客户名称": "新昌县亚鑫科技有限公司", "贷款余额": "2 亿"},
        ]

        payload = _build_sql_result_chart_payload(
            state=state,
            question=question,
            sql=sql,
            columns=columns,
            column_display_names=columns,
            rows=rows,
        )

        assert payload is not None
        self.assertEqual(payload["y_key"], "贷款余额")
        self.assertEqual(payload["x_key"], "客户名称")
        self.assertEqual(len(payload["data"]), 3)
        labels = [str(item.get("客户名称")) for item in payload["data"]]
        self.assertTrue(any("2009001293" in label for label in labels))


    def test_pick_chart_axes_uses_display_name_to_avoid_identifier_as_measure(self):
        columns = ["cust_seq", "cust_name", "loan_bal"]
        rows = [
            {"cust_seq": "2009001293", "cust_name": "-", "loan_bal": "15.26 亿"},
            {"cust_seq": "2000045474", "cust_name": "-", "loan_bal": "6.92 亿"},
            {"cust_seq": "2000068157", "cust_name": "新昌县亚鑫科技有限公司", "loan_bal": "2 亿"},
        ]
        display_name_map = {
            "cust_seq": "客户统一编号",
            "cust_name": "客户名称",
            "loan_bal": "贷款余额",
        }

        x_key, y_key = _pick_chart_axes(
            columns,
            rows,
            column_data_type_map={},
            column_display_name_map=display_name_map,
        )

        self.assertEqual(x_key, "cust_name")
        self.assertEqual(y_key, "loan_bal")

    @patch("app.ai.workflow.data_graph._load_column_data_type_map", return_value={})
    def test_build_chart_payload_keeps_unique_points_when_name_missing(self, _mock_type_map):
        state = {"viz_type": "柱状图", "data_intent": "visualization"}
        columns = ["cust_seq", "cust_name", "loan_bal"]
        column_display_names = ["客户统一编号", "客户名称", "贷款余额"]
        rows = [
            {"cust_seq": "2009001293", "cust_name": "-", "loan_bal": "15.26 亿"},
            {"cust_seq": "2000045474", "cust_name": "-", "loan_bal": "6.92 亿"},
            {"cust_seq": "2000068157", "cust_name": "新昌县亚鑫科技有限公司", "loan_bal": "2 亿"},
        ]

        payload = _build_sql_result_chart_payload(
            state=state,
            question="查询2025年6月30日贷款余额前10名的客户",
            sql="SELECT cust_seq, cust_name, loan_bal FROM fdmdata.f_mid_loan_tb LIMIT 10",
            columns=columns,
            column_display_names=column_display_names,
            rows=rows,
        )

        assert payload is not None
        self.assertEqual(payload["x_key"], "cust_name")
        self.assertEqual(payload["y_key"], "loan_bal")
        self.assertEqual(len(payload["data"]), 3)

        labels = [str(item.get("cust_name", "")) for item in payload["data"]]
        self.assertEqual(len(set(labels)), 3)
        self.assertTrue(any(label.startswith("未知（2009001293") for label in labels))
        self.assertTrue(any(label.startswith("未知（2000045474") for label in labels))


    def test_pick_chart_axes_prefers_org_name_when_org_dimension_requested(self):
        columns = ["org_cd", "org_nm", "loan_bal"]
        rows = [
            {"org_cd": "330101", "org_nm": "嘉兴分行", "loan_bal": "15.26 亿"},
            {"org_cd": "330102", "org_nm": "绍兴分行", "loan_bal": "6.92 亿"},
            {"org_cd": "330103", "org_nm": "宁波分行", "loan_bal": "2 亿"},
        ]
        display_name_map = {
            "org_cd": "机构编号",
            "org_nm": "机构名称",
            "loan_bal": "贷款余额",
        }

        x_key, y_key = _pick_chart_axes(
            columns,
            rows,
            column_data_type_map={},
            column_display_name_map=display_name_map,
            dimension_hints=["机构"],
            metric_hint="贷款余额",
        )

        self.assertEqual(x_key, "org_nm")
        self.assertEqual(y_key, "loan_bal")

    @patch("app.ai.workflow.data_graph._load_column_data_type_map", return_value={})
    def test_build_chart_payload_uses_state_semantic_context_for_axis(self, _mock_type_map):
        state = {
            "viz_type": "柱状图",
            "data_intent": "visualization",
            "dimensions": ["机构"],
            "matched_metric": "贷款余额",
            "query_context": {
                "analysis": {
                    "dimensions": ["机构"],
                    "metric_name": "贷款余额",
                }
            },
        }
        columns = ["org_cd", "org_nm", "loan_amt"]
        rows = [
            {"org_cd": "330101", "org_nm": "嘉兴分行", "loan_amt": "15.26 亿"},
            {"org_cd": "330102", "org_nm": "绍兴分行", "loan_amt": "6.92 亿"},
            {"org_cd": "330103", "org_nm": "宁波分行", "loan_amt": "2 亿"},
        ]

        payload = _build_sql_result_chart_payload(
            state=state,
            question="查询2025年6月30日贷款余额前10名机构并用柱状图展示",
            sql="SELECT org_cd, org_nm, loan_amt FROM fdmdata.f_mid_loan_tb LIMIT 10",
            columns=columns,
            column_display_names=columns,
            rows=rows,
        )

        assert payload is not None
        self.assertEqual(payload["x_key"], "org_nm")
        self.assertEqual(payload["y_key"], "loan_amt")
        self.assertEqual(len(payload["data"]), 3)

    def test_derive_metric_sql_for_topn_customer(self):
        template = (
            "SELECT SUM(prin_bal) AS 贷款余额 "
            "FROM fdmdata.f_mid_loan_k_tb "
            "WHERE ccy_cd = 'CNY' AND data_dt = '${data_dt}'"
        )
        question = "查询2025年6月30日贷款余额前10名的客户"

        derived = _derive_metric_sql(
            query_template=template,
            time_range="2025年6月30日",
            question=question,
            dimensions=["客户"],
        )

        self.assertIsNotNone(derived)
        assert derived is not None
        self.assertIn("SUM(prin_bal)", derived)
        self.assertIn("ecif_cust_no", derived)
        self.assertIn("GROUP BY ecif_cust_no", derived)
        self.assertIn("ORDER BY", derived)
        self.assertIn("LIMIT 10", derived)
        self.assertIn("data_dt = '20250630'", derived)

    def test_derive_metric_sql_for_org_dimension_maps_to_org_tree(self):
        template = (
            "SELECT SUM(prin_bal) AS 贷款余额 "
            "FROM fdmdata.f_mid_loan_k_tb "
            "WHERE ccy_cd = 'CNY' AND data_dt = '${data_dt}'"
        )
        question = "查询2025年6月30日按机构分组贷款余额前10名"

        derived = _derive_metric_sql(
            query_template=template,
            time_range="2025年6月30日",
            question=question,
            dimensions=["机构"],
        )

        self.assertIsNotNone(derived)
        assert derived is not None
        self.assertIn("JOIN fdmdata.f_mid_org_tree_k o", derived)
        self.assertIn("o.org_lv = '04'", derived)
        self.assertIn("o.org_no AS org_no", derived)
        self.assertIn("o.org_val AS org_name", derived)
        self.assertIn("SUM(t.prin_bal)", derived)
        self.assertIn("GROUP BY o.org_no, o.org_val", derived)
        self.assertNotIn("GROUP BY legal_org_cd", derived)

    def test_org_dimension_sql_rejects_legal_org_cd_only_grouping(self):
        sql = (
            "SELECT legal_org_cd, SUM(prin_bal) AS loan_bal "
            "FROM fdmdata.f_mid_loan_k_tb "
            "WHERE data_dt = '20250630' "
            "GROUP BY legal_org_cd"
        )

        self.assertFalse(
            _is_sql_semantically_compatible(
                sql=sql,
                question="查询2025年6月30日各机构贷款余额",
                dimensions=["机构"],
            )
        )

    def test_metric_resolve_integration_org_prompt_generates_org_tree_sql(self):
        prompt = "查询2025年6月30日各机构贷款余额前10名"
        llm_payload = {
            "intent": "metric_query",
            "metric_name": "贷款余额",
            "time_range": "2025年6月30日",
            "filters": [],
            "dimensions": ["机构"],
            "chart_type": "",
            "clarification_needed": "",
        }
        metric_template = (
            "SELECT SUM(prin_bal) AS 贷款余额 "
            "FROM fdmdata.f_mid_loan_k_tb "
            "WHERE ccy_cd = 'CNY' AND data_dt = '${data_dt}'"
        )
        metric_candidates = [
            {
                "metric_id": "LOAN_BALANCE",
                "metric_name": "贷款余额",
                "query_template": metric_template,
                "similarity": 1.0,
            }
        ]

        with patch("app.ai.workflow.data_graph.get_scene_llm", return_value=_FakeLLM(llm_payload)):
            analyzed_state = analyze_data_intent({"messages": [HumanMessage(content=prompt)]})

        with patch("app.ai.workflow.data_graph._search_metrics_exact_name", return_value=metric_candidates):
            resolved = metric_resolve(
                {
                    "query_context": analyzed_state.get("query_context", {}),
                    "matched_metric": analyzed_state.get("matched_metric"),
                    "time_range": analyzed_state.get("time_range"),
                    "dimensions": analyzed_state.get("dimensions"),
                }
            )

        sql = str(resolved.get("generated_sql") or "")
        self.assertEqual(resolved.get("sql_source"), "metric")
        self.assertIn("JOIN fdmdata.f_mid_org_tree_k o", sql)
        self.assertIn("o.org_no AS org_no", sql)
        self.assertIn("o.org_val AS org_name", sql)
        self.assertIn("GROUP BY o.org_no, o.org_val", sql)
        self.assertNotIn("GROUP BY legal_org_cd", sql)

    def test_metric_resolve_preserves_topn_contract_when_continuation_summary_drops_topn_phrase(self):
        metric_template = (
            "SELECT SUM(prin_bal) AS 贷款余额 "
            "FROM fdmdata.f_mid_loan_k_tb "
            "WHERE ccy_cd = 'CNY' AND data_dt = '${data_dt}'"
        )
        metric_candidates = [
            {
                "metric_id": "LOAN_001",
                "metric_name": "贷款余额",
                "query_template": metric_template,
                "similarity": 1.0,
            }
        ]

        with patch("app.ai.workflow.data_graph._search_metrics_exact_name", return_value=metric_candidates):
            resolved = metric_resolve(
                {
                    "query_context": {
                        "original_question": "查询贷款余额，时间范围2025-06-30，按客户聚合",
                        "query_shape": "top_n",
                        "ranking": {"limit": 10, "sort_by": "贷款余额", "sort_order": "desc"},
                    },
                    "session_frame": {
                        "metric": "贷款余额",
                        "time_range": "2025-06-30",
                        "dimensions": ["客户"],
                        "query_shape": "top_n",
                        "ranking": {"limit": 10, "sort_by": "贷款余额", "sort_order": "desc"},
                    },
                    "matched_metric": "贷款余额",
                    "time_range": "2025-06-30",
                    "dimensions": ["客户"],
                }
            )

        sql = str(resolved.get("generated_sql") or "")
        self.assertEqual(resolved.get("sql_source"), "metric")
        self.assertIn("GROUP BY ecif_cust_no", sql)
        self.assertIn("ORDER BY 贷款余额 DESC", sql)
        self.assertIn("LIMIT 10", sql)

    def test_derive_metric_sql_returns_none_when_dimension_unmapped(self):
        template = (
            "SELECT SUM(prin_bal) AS 贷款余额 "
            "FROM fdmdata.f_mid_loan_k_tb "
            "WHERE ccy_cd = 'CNY' AND data_dt = '${data_dt}'"
        )

        derived = _derive_metric_sql(
            query_template=template,
            time_range="2025年6月30日",
            question="查询2025年6月30日贷款余额前10名客户",
            dimensions=["未知维度"],
        )

        self.assertIsNone(derived)

    def test_result_enrich_not_triggered_without_customer_id(self):
        rows = [{"贷款余额": 123.45}]
        cols = ["贷款余额"]

        rule = ResultLookupEnrichmentRuleConfig(
            name="customer_name",
            key_column_candidates=("ecif_cust_no",),
            target_column="客户名称",
            source_table="fdmdata.f_mid_dep_tb",
            source_key_column="ecif_cust_no",
            source_value_column="cust_acct_name",
            source_date_column="data_dt",
            result_date_column_candidates=("data_dt",),
        )

        with patch(
            "app.ai.workflow.data_graph._load_runtime_result_enrichment_rules",
            return_value=(rule,),
        ):
            new_rows, new_cols = _enrich_result_rows_if_needed(rows, cols)

        self.assertEqual(new_rows, rows)
        self.assertEqual(new_cols, cols)

    def test_result_enrich_not_triggered_if_name_exists(self):
        rows = [{"ecif_cust_no": "1001", "客户名称": "测试客户", "贷款余额": 100.0}]
        cols = ["ecif_cust_no", "客户名称", "贷款余额"]

        rule = ResultLookupEnrichmentRuleConfig(
            name="customer_name",
            key_column_candidates=("ecif_cust_no",),
            target_column="客户名称",
            source_table="fdmdata.f_mid_dep_tb",
            source_key_column="ecif_cust_no",
            source_value_column="cust_acct_name",
            source_date_column="data_dt",
            result_date_column_candidates=("data_dt",),
        )

        with patch(
            "app.ai.workflow.data_graph._load_runtime_result_enrichment_rules",
            return_value=(rule,),
        ):
            new_rows, new_cols = _enrich_result_rows_if_needed(rows, cols)

        self.assertEqual(new_rows, rows)
        self.assertEqual(new_cols, cols)

    def test_result_enrich_appends_name_column(self):
        rows = [{"data_dt": "2025-06-30", "ecif_cust_no": "1001", "贷款余额": 100.0}]
        cols = ["data_dt", "ecif_cust_no", "贷款余额"]

        rule = ResultLookupEnrichmentRuleConfig(
            name="customer_name",
            key_column_candidates=("ecif_cust_no",),
            target_column="客户名称",
            source_table="fdmdata.f_mid_dep_tb",
            source_key_column="ecif_cust_no",
            source_value_column="cust_acct_name",
            source_date_column="data_dt",
            result_date_column_candidates=("data_dt",),
        )

        with patch(
            "app.ai.workflow.data_graph._load_runtime_result_enrichment_rules",
            return_value=(rule,),
        ), patch(
            "app.ai.workflow.data_graph._fetch_lookup_value_map",
            return_value={"1001": "测试客户A"},
        ):
            new_rows, new_cols = _enrich_result_rows_if_needed(rows, cols)

        self.assertEqual(new_cols, ["data_dt", "ecif_cust_no", "客户名称", "贷款余额"])
        self.assertEqual(new_rows[0]["客户名称"], "测试客户A")

    def test_build_column_display_names_with_mapping(self):
        cols = ["data_dt", "ecif_cust_no", "客户名称", "loan_bal_amt"]
        display_map = {
            "data_dt": "数据日期",
            "ecif_cust_no": "客户编号",
            "loan_bal_amt": "贷款余额",
        }

        result = _build_column_display_names(cols, display_map)

        self.assertEqual(result, ["数据日期", "客户编号", "客户名称", "贷款余额"])

    def test_build_column_display_names_fallback_to_original(self):
        cols = ["data_dt", "unknown_col"]
        display_map = {"data_dt": "数据日期"}

        result = _build_column_display_names(cols, display_map)

        self.assertEqual(result, ["数据日期", "unknown_col"])

    def test_build_display_sql_only_alias_plain_columns(self):
        sql = "SELECT data_dt, ecif_cust_no, SUM(loan_bal_amt) AS loan_balance FROM fdmdata.f_mid_loan_k_tb"
        display_map = {
            "data_dt": "数据日期",
            "ecif_cust_no": "客户编号",
            "loan_bal_amt": "贷款余额",
        }

        display_sql = _build_display_sql(sql, display_map)

        self.assertIn('data_dt AS "数据日期"', display_sql)
        self.assertIn('ecif_cust_no AS "客户编号"', display_sql)
        self.assertIn("SUM(loan_bal_amt) AS loan_balance", display_sql)

    def test_build_display_sql_keeps_existing_alias(self):
        sql = "SELECT data_dt AS dt, ecif_cust_no FROM fdmdata.f_mid_loan_k_tb"
        display_map = {
            "data_dt": "数据日期",
            "ecif_cust_no": "客户编号",
        }

        display_sql = _build_display_sql(sql, display_map)

        self.assertIn("data_dt AS dt", display_sql)
        self.assertIn('ecif_cust_no AS "客户编号"', display_sql)

    def test_build_display_sql_returns_original_on_parse_error(self):
        sql = "SELECT FROM"
        display_map = {"data_dt": "数据日期"}

        display_sql = _build_display_sql(sql, display_map)

        self.assertEqual(display_sql, sql)

    @patch("app.ai.workflow.data_graph.extract_tables_from_sql", return_value={"fdmdata.f_mid_loan_k_tb"})
    @patch("app.ai.workflow.data_graph.engine")
    def test_load_column_display_name_map_prefers_table_filtered_result(self, mock_engine, _mock_extract):
        class _Result:
            def __init__(self, rows):
                self._rows = rows

            def fetchall(self):
                return self._rows

        class _Conn:
            def __init__(self):
                self.called = 0

            def execute(self, _query, _params):
                self.called += 1
                if self.called == 1:
                    return _Result([
                        type("Row", (), {"column_name": "data_dt", "display_name": "数据日期"})(),
                        type("Row", (), {"column_name": "loan_bal_amt", "display_name": "贷款余额"})(),
                    ])
                return _Result([])

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        mock_engine.connect.return_value = _Conn()

        mapping = _load_column_display_name_map(
            columns=["data_dt", "loan_bal_amt"],
            sql="SELECT data_dt, loan_bal_amt FROM fdmdata.f_mid_loan_k_tb",
        )

        self.assertEqual(mapping["data_dt"], "数据日期")
        self.assertEqual(mapping["loan_bal_amt"], "贷款余额")

    @patch("app.ai.workflow.data_graph.extract_tables_from_sql", return_value={"fdmdata.f_mid_loan_k_tb"})
    @patch("app.ai.workflow.data_graph.engine")
    def test_load_column_display_name_map_fallback_global_when_filtered_empty(self, mock_engine, _mock_extract):
        class _Result:
            def __init__(self, rows):
                self._rows = rows

            def fetchall(self):
                return self._rows

        class _Conn:
            def __init__(self):
                self.called = 0

            def execute(self, _query, _params):
                self.called += 1
                if self.called == 1:
                    return _Result([])
                return _Result([
                    type("Row", (), {"column_name": "ecif_cust_no", "display_name": "客户编号"})(),
                ])

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        mock_engine.connect.return_value = _Conn()

        mapping = _load_column_display_name_map(
            columns=["ecif_cust_no"],
            sql="SELECT ecif_cust_no FROM fdmdata.f_mid_loan_k_tb",
        )

        self.assertEqual(mapping["ecif_cust_no"], "客户编号")


if __name__ == "__main__":
    unittest.main()
