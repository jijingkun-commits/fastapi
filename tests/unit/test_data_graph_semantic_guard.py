"""问数 SQL 候选语义护栏单元测试。"""

import unittest
from unittest.mock import patch

from app.services.result_enrichment_rule_service import ResultLookupEnrichmentRuleConfig

from app.ai.workflow.data_graph import (
    _build_column_display_names,
    _build_display_sql,
    _derive_metric_sql,
    _enrich_result_rows_if_needed,
    _extract_top_n,
    _is_sql_semantically_compatible,
    _load_column_display_name_map,
    _requires_detail_query,
)


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
