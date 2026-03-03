"""聊天文档记忆单开关解析测试。"""

from app.services import chat_service


def test_document_memory_recall_switch_should_follow_master_config(monkeypatch) -> None:  # noqa: ANN001
    """召回开关应统一跟随 feature.enable_document_memory。"""

    monkeypatch.delenv("ENABLE_DOCUMENT_MEMORY", raising=False)
    captured: list[str] = []

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            captured.append(key)
            return True

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_document_memory_recall_enabled(False) is True
    assert captured == ["feature.enable_document_memory"]


def test_document_memory_flush_switch_should_follow_master_env_override(monkeypatch) -> None:  # noqa: ANN001
    """写入开关应统一跟随 ENABLE_DOCUMENT_MEMORY 环境变量。"""

    monkeypatch.setenv("ENABLE_DOCUMENT_MEMORY", "false")

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            return True

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_document_memory_flush_enabled(True) is False


def test_document_memory_hybrid_switch_should_follow_master_config(monkeypatch) -> None:  # noqa: ANN001
    """混合检索开关应统一跟随 feature.enable_document_memory。"""

    monkeypatch.delenv("ENABLE_DOCUMENT_MEMORY", raising=False)
    captured: list[str] = []

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            captured.append(key)
            return False

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_document_memory_hybrid_enabled(True) is False
    assert captured == ["feature.enable_document_memory"]
