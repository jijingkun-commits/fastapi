"""聊天服务文档记忆混合检索开关测试。"""

from app.services import chat_service


def test_document_memory_hybrid_flag_reads_config_resolver(monkeypatch) -> None:  # noqa: ANN001
    """环境变量未显式设置时应读取 ConfigResolver。"""

    monkeypatch.delenv("ENABLE_DOCUMENT_MEMORY_HYBRID_SEARCH", raising=False)

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            if key == "feature.enable_document_memory_hybrid_search":
                return True
            return default

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_document_memory_hybrid_enabled(False) is True


def test_document_memory_hybrid_flag_env_override(monkeypatch) -> None:  # noqa: ANN001
    """环境变量显式值应覆盖配置中心。"""

    monkeypatch.setenv("ENABLE_DOCUMENT_MEMORY_HYBRID_SEARCH", "false")

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            if key == "feature.enable_document_memory_hybrid_search":
                return True
            return default

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_document_memory_hybrid_enabled(True) is False


def test_document_memory_hybrid_min_score_clamped_to_non_negative(monkeypatch) -> None:  # noqa: ANN001
    """最小分阈值应裁剪为非负数。"""

    class _Resolver:
        @classmethod
        def get_float(cls, key: str, default: float = 0.0) -> float:  # noqa: ARG003
            return -0.5

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._get_document_memory_hybrid_min_score(0.1) == 0.0
