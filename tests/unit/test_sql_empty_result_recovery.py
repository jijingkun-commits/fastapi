"""SQL 空结果恢复工具单元测试。"""
import unittest

from app.ai.utils.sql_empty_result_recovery import (
    extract_data_dt_from_sql,
    is_effectively_empty_result,
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


if __name__ == "__main__":
    unittest.main()

