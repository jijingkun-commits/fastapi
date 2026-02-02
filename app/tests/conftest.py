"""app/tests 目录的 pytest 配置（中文注释）。

复用 tests/conftest.py 中的 fixture，保持测试配置统一。
"""
# 从根目录 tests/conftest.py 导入所有 fixture
# pytest 会自动发现并使用这些 fixture
import sys
from pathlib import Path

# 确保能导入 tests 模块
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# 重新导出所有 fixture
from tests.conftest import (
    test_engine,
    db_session,
    client,
    mock_db_session,
    auth_headers,
    test_user_id,
    setup_test_environment,
)

__all__ = [
    "test_engine",
    "db_session", 
    "client",
    "mock_db_session",
    "auth_headers",
    "test_user_id",
    "setup_test_environment",
]
