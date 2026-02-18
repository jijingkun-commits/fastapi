"""SQL 空结果恢复工具单元测试。"""
import unittest

from app.ai.utils.sql_empty_result_recovery import (
    extract_data_dt_from_sql,
    is_effectively_empty_result,
    rewrite_sql_for_column_compatibility,
    rewrite_sql_for_empty_result,
)


class TestIsEffectivelyEmptyResult(unittest.TestCase):
    """测试空结果判定。"""

    def test_empty_list(self):
        self.assertTrue(is_effectively_empty_result([]))

    def test_single_none_row(self):
        self.assertTrue(is_effectively_empty_result([{"sum": None}]))

    def test_single_non_none_row(self):
        self.assertFalse(is_effectively_empty_result([{"sum": 1}]))

    def test_multi_rows(self):
        self.assertFalse(is_effectively_empty_result([{"a": 1}, {"a": None}]))


class TestExtractDataDtFromSql(unittest.TestCase):
    """测试 data_dt 提取。"""

    def test_extract_yyyy_mm_dd(self):
        sql = "SELECT * FROM t WHERE data_dt = '2025-06-30'"
        self.assertEqual(extract_data_dt_from_sql(sql), "2025-06-30")

    def test_extract_yyyymmdd(self):
        sql = "SELECT * FROM t WHERE data_dt='20250630'"
        self.assertEqual(extract_data_dt_from_sql(sql), "2025-06-30")

    def test_extract_not_found(self):
        sql = "SELECT * FROM t WHERE biz_dt='2025-06-30'"
        self.assertIsNone(extract_data_dt_from_sql(sql))


class TestRewriteSqlForEmptyResult(unittest.TestCase):
    """测试空结果 SQL 重写。"""

    def test_rewrite_when_probe_has_rows(self):
        sql = (
            "SELECT SUM(prin_bal) FROM fdmdata.f_mid_loan_tb "
            "WHERE data_dt = '2025-06-30'"
        )

        def probe(_table: str, _data_dt: str) -> bool:
            return True

        rewritten, reason = rewrite_sql_for_empty_result(sql, probe_has_rows=probe)

        self.assertIn("f_mid_loan_k_tb", rewritten)
        self.assertNotIn("f_mid_loan_tb", rewritten.lower())
        self.assertIsNotNone(reason)

    def test_no_rewrite_when_probe_no_rows(self):
        sql = (
            "SELECT SUM(prin_bal) FROM fdmdata.f_mid_loan_tb "
            "WHERE data_dt = '2025-06-30'"
        )

        def probe(_table: str, _data_dt: str) -> bool:
            return False

        rewritten, reason = rewrite_sql_for_empty_result(sql, probe_has_rows=probe)

        self.assertEqual(rewritten, sql)
        self.assertIsNone(reason)

    def test_no_rewrite_for_other_tables(self):
        sql = "SELECT * FROM fdmdata.f_mid_dep_tb WHERE data_dt='2025-06-30'"

        def probe(_table: str, _data_dt: str) -> bool:
            return True

        rewritten, reason = rewrite_sql_for_empty_result(sql, probe_has_rows=probe)

        self.assertEqual(rewritten, sql)
        self.assertIsNone(reason)

    def test_rewrite_with_column_mapping(self):
        sql = (
            "SELECT t.data_dt, t.org_cd AS 机构编码, t.level7_val AS 法人机构名称, SUM(t.prin_bal) AS 贷款余额 "
            "FROM fdmdata.f_mid_loan_tb AS t "
            "WHERE t.data_dt = '2025-06-30' "
            "GROUP BY t.data_dt, t.org_cd, t.level7_val"
        )

        def probe(_table: str, _data_dt: str) -> bool:
            return True

        rewritten, reason = rewrite_sql_for_empty_result(sql, probe_has_rows=probe)

        self.assertIn("f_mid_loan_k_tb", rewritten)
        self.assertIn("t.dept_cd", rewritten)
        self.assertIn("t.dept_val", rewritten)
        self.assertNotIn("t.org_cd", rewritten)
        self.assertNotIn("t.level7_val", rewritten)
        self.assertIsNotNone(reason)

    def test_column_mapping_only_applies_to_target_table_alias(self):
        sql = (
            "SELECT t.org_cd, o.level7_val "
            "FROM fdmdata.f_mid_loan_tb t "
            "JOIN fdmdata.f_mid_org_tree o ON t.org_cd = o.org_no "
            "WHERE t.data_dt = '2025-06-30'"
        )

        def probe(_table: str, _data_dt: str) -> bool:
            return True

        rewritten, _ = rewrite_sql_for_empty_result(sql, probe_has_rows=probe)

        self.assertIn("t.dept_cd", rewritten)
        self.assertIn("o.level7_val", rewritten)

    def test_rewrite_rule_compatible_with_legacy_three_tuple(self):
        sql = (
            "SELECT org_cd FROM fdmdata.f_mid_loan_tb "
            "WHERE data_dt = '2025-06-30'"
        )

        def probe(_table: str, _data_dt: str) -> bool:
            return True

        rewritten, reason = rewrite_sql_for_empty_result(
            sql,
            probe_has_rows=probe,
            rewrite_rules=[
                (
                    "fdmdata.f_mid_loan_tb",
                    "fdmdata.f_mid_loan_k_tb",
                    "legacy rule",
                )
            ],
        )

        self.assertIn("f_mid_loan_k_tb", rewritten)
        self.assertIn("org_cd", rewritten)
        self.assertEqual(reason, "legacy rule")


class TestRewriteSqlForColumnCompatibility(unittest.TestCase):
    """测试字段兼容 SQL 重写。"""

    def test_rewrite_column_for_single_target_table(self):
        sql = (
            "SELECT t.org_cd, t.level7_val FROM fdmdata.f_mid_loan_k_tb t "
            "WHERE t.data_dt = '2025-06-30'"
        )

        rewritten, reason = rewrite_sql_for_column_compatibility(sql)

        self.assertIn("t.dept_cd", rewritten)
        self.assertIn("t.dept_val", rewritten)
        self.assertNotIn("t.org_cd", rewritten)
        self.assertNotIn("t.level7_val", rewritten)
        self.assertIsNotNone(reason)

    def test_rewrite_column_by_error_message_filter(self):
        sql = (
            "SELECT t.org_cd, t.level7_val FROM fdmdata.f_mid_loan_k_tb t "
            "WHERE t.data_dt = '2025-06-30'"
        )

        rewritten, reason = rewrite_sql_for_column_compatibility(
            sql,
            error_message='column t.level7_val does not exist',
        )

        self.assertIn("t.level7_val", sql)
        self.assertIn("t.org_cd", rewritten)
        self.assertIn("t.dept_val", rewritten)
        self.assertNotIn("t.level7_val", rewritten)
        self.assertEqual(reason, "检测到字段不兼容，已自动替换字段: level7_val->dept_val")

    def test_no_rewrite_for_non_column_error(self):
        sql = "SELECT * FROM fdmdata.f_mid_loan_k_tb"

        rewritten, reason = rewrite_sql_for_column_compatibility(
            sql,
            error_message='permission denied for table f_mid_loan_k_tb',
        )

        self.assertEqual(rewritten, sql)
        self.assertIsNone(reason)


if __name__ == "__main__":
    unittest.main()
