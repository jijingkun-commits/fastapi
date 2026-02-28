"""聊天偏好记忆统一开关解析测试。"""

from app.services import chat_service


def test_memory_feature_reads_config_resolver_when_env_absent(monkeypatch) -> None:  # noqa: ANN001
    """环境变量未显式设置时，应按 ConfigResolver 结果生效。"""

    monkeypatch.delenv("ENABLE_USER_PREFERENCE_MEMORY", raising=False)

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            if key == "feature.enable_user_preference_memory":
                return True
            return default

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_user_preference_memory_enabled(False) is True


def test_memory_feature_env_override_has_higher_priority(monkeypatch) -> None:  # noqa: ANN001
    """环境变量显式设置时，应覆盖 ConfigResolver 值。"""

    monkeypatch.setenv("ENABLE_USER_PREFERENCE_MEMORY", "false")

    class _Resolver:
        @classmethod
        def get_bool(cls, key: str, default: bool = False) -> bool:  # noqa: ARG003
            if key == "feature.enable_user_preference_memory":
                return True
            return default

    monkeypatch.setattr("app.services.config_resolver.ConfigResolver", _Resolver)

    assert chat_service._is_user_preference_memory_enabled(False) is False
