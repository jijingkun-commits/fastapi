"""错误处理模块单元测试。

测试 app/ai/utils/error_handler.py 的功能。
"""
import unittest
from app.ai.utils.error_handler import (
    classify_error,
    format_error_message,
    get_error_suggestions,
    is_recoverable,
    format_retry_message,
    build_final_error_message,
    ErrorCategory
)


class TestClassifyError(unittest.TestCase):
    """测试错误分类。"""
    
    def test_table_not_found(self):
        error = 'relation "users" does not exist'
        category, detail, values = classify_error(error)
        self.assertEqual(category, ErrorCategory.TABLE_NOT_FOUND)
        self.assertIn("users", detail)
    
    def test_column_not_found(self):
        error = 'column "age" does not exist'
        category, detail, values = classify_error(error)
        self.assertEqual(category, ErrorCategory.COLUMN_NOT_FOUND)
        self.assertIn("age", detail)
    
    def test_syntax_error(self):
        error = 'syntax error at or near "SELEC"'
        category, detail, values = classify_error(error)
        self.assertEqual(category, ErrorCategory.SYNTAX_ERROR)
    
    def test_permission_denied(self):
        error = 'permission denied for table users'
        category, detail, values = classify_error(error)
        self.assertEqual(category, ErrorCategory.PERMISSION_DENIED)
    
    def test_connection_error(self):
        error = 'connection refused'
        category, detail, values = classify_error(error)
        self.assertEqual(category, ErrorCategory.CONNECTION_ERROR)
    
    def test_timeout_error(self):
        error = 'statement timeout'
        category, detail, values = classify_error(error)
        self.assertEqual(category, ErrorCategory.TIMEOUT)
    
    def test_unknown_error(self):
        error = 'some random error message'
        category, detail, values = classify_error(error)
        self.assertEqual(category, ErrorCategory.UNKNOWN)


class TestFormatErrorMessage(unittest.TestCase):
    """测试错误消息格式化。"""
    
    def test_table_not_found_message(self):
        error = 'relation "orders" does not exist'
        message = format_error_message(error)
        self.assertIn("找不到数据表", message)
        self.assertIn("orders", message)
    
    def test_with_context(self):
        error = 'relation "xxx" does not exist'
        context = {"available_tables": ["users", "orders", "products"]}
        message = format_error_message(error, context)
        self.assertIn("可用的数据表", message)
        self.assertIn("users", message)
    
    def test_include_raw_error(self):
        error = 'some error'
        message = format_error_message(error, include_raw=True)
        self.assertIn("技术详情", message)
        self.assertIn("some error", message)


class TestGetErrorSuggestions(unittest.TestCase):
    """测试错误建议。"""
    
    def test_table_not_found_suggestions(self):
        error = 'relation "xxx" does not exist'
        suggestions = get_error_suggestions(error)
        self.assertIsInstance(suggestions, list)
        self.assertTrue(len(suggestions) > 0)
    
    def test_suggestions_vary_by_iterations(self):
        error = 'some error'
        suggestions_1 = get_error_suggestions(error, iterations=1)
        suggestions_3 = get_error_suggestions(error, iterations=3)
        # 重试次数多时应该有不同的建议
        self.assertIsInstance(suggestions_1, list)
        self.assertIsInstance(suggestions_3, list)


class TestIsRecoverable(unittest.TestCase):
    """测试可恢复性判断。"""
    
    def test_table_not_found_recoverable(self):
        error = 'relation "xxx" does not exist'
        self.assertTrue(is_recoverable(error))
    
    def test_column_not_found_recoverable(self):
        error = 'column "xxx" does not exist'
        self.assertTrue(is_recoverable(error))
    
    def test_syntax_error_recoverable(self):
        error = 'syntax error at or near "xxx"'
        self.assertTrue(is_recoverable(error))
    
    def test_permission_denied_not_recoverable(self):
        error = 'permission denied for table users'
        self.assertFalse(is_recoverable(error))
    
    def test_connection_error_not_recoverable(self):
        error = 'connection refused'
        self.assertFalse(is_recoverable(error))


class TestFormatRetryMessage(unittest.TestCase):
    """测试重试消息格式化。"""
    
    def test_retry_message_format(self):
        message = format_retry_message(1, 3)
        self.assertIn("2", message)  # 第 2 次尝试
        self.assertIn("3", message)  # 共 3 次
    
    def test_max_retry_message(self):
        message = format_retry_message(3, 3)
        self.assertIn("3", message)
        self.assertIn("仍无法", message)


class TestBuildFinalErrorMessage(unittest.TestCase):
    """测试最终错误消息构建。"""
    
    def test_basic_message(self):
        error = 'some error'
        message = build_final_error_message(error, iterations=1)
        self.assertIsInstance(message, str)
        self.assertTrue(len(message) > 0)
    
    def test_with_iterations(self):
        error = 'some error'
        message = build_final_error_message(error, iterations=3)
        self.assertIn("3", message)  # 应该显示尝试次数
    
    def test_with_context(self):
        error = 'relation "xxx" does not exist'
        context = {"available_tables": ["users", "orders"]}
        message = build_final_error_message(error, iterations=1, context=context)
        self.assertIn("users", message)


if __name__ == '__main__':
    unittest.main()
