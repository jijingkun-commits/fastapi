"""pytest 全局配置与通用 fixture（中文注释）。

提供测试通用的数据库会话、认证令牌、测试客户端等 fixture，
支持测试隔离与资源复用。
"""
import os
import pytest
from typing import Generator
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# 设置测试环境
os.environ.setdefault("ENV", "test")

from app.main import app
from app.db.session import get_db
from app.core.config import DATABASE_URL


# 测试数据库 URL（使用主库或专用测试库）
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", DATABASE_URL)


@pytest.fixture(scope="session")
def test_engine():
    """创建测试用数据库引擎（会话级别共享）。"""
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """提供测试级别的数据库会话。
    
    每个测试函数独立的事务，测试结束后自动回滚。
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """提供 FastAPI 测试客户端，自动注入测试数据库会话。"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def mock_db_session() -> MagicMock:
    """提供 Mock 数据库会话，用于单元测试。"""
    mock_session = MagicMock(spec=Session)
    mock_session.execute.return_value = MagicMock()
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    return mock_session


@pytest.fixture(scope="function")
def auth_headers() -> dict:
    """提供测试用认证头。
    
    注意：这是一个简化的测试令牌，实际测试可能需要
    通过 /api/v1/login 获取真实令牌。
    """
    # 测试环境使用固定的测试令牌
    test_token = os.getenv("TEST_AUTH_TOKEN", "test-token-for-ci")
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture(scope="function")
def test_user_id() -> int:
    """提供测试用户 ID。"""
    return int(os.getenv("TEST_USER_ID", "1"))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """测试环境初始化（自动执行）。"""
    # 可在此处添加测试环境的全局初始化逻辑
    # 例如：创建测试数据库表、插入基础数据等
    yield
    # 清理逻辑
