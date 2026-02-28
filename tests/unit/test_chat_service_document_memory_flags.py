"""聊天文档记忆开关解析测试。"""

from app.services import chat_service


def test_document_memory_feature_reads_config_resolver(monkeypatch) -> None:  # noqa: ANN001
    """环境变量未显式设置时，应按 ConfigResolver 结果生效。"""

    monkeypatch.delenv("ENABLE_DOCUMENT_MEMORY", raising=False)

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            if key == "feature.enable_document_memory":
                return True
            return default

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_document_memory_enabled(False) is True


def test_document_memory_feature_env_override(monkeypatch) -> None:  # noqa: ANN001
    """环境变量显式设置时，应覆盖 ConfigResolver 值。"""

    monkeypatch.setenv("ENABLE_DOCUMENT_MEMORY", "false")

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            if key == "feature.enable_document_memory":
                return True
            return default

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_document_memory_enabled(True) is False


def test_document_memory_weights_are_normalized() -> None:
    """权重总和不为 1 时应自动归一化。"""

    vector_weight, text_weight = chat_service._get_document_memory_weights(7.0, 3.0)
    assert round(vector_weight + text_weight, 6) == 1.0
    assert round(vector_weight, 6) == 0.7
    assert round(text_weight, 6) == 0.3

