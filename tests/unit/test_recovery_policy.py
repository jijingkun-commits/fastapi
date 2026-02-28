"""运行时恢复策略模块测试。"""

from app.ai.runtime import recovery_policy


def test_is_feature_flag_enabled_should_use_fallback_when_env_missing(monkeypatch) -> None:  # noqa: ANN001
    """环境变量缺失时返回 fallback。"""

    monkeypatch.delenv("UNIT_TEST_FLAG", raising=False)
    assert recovery_policy.is_feature_flag_enabled("UNIT_TEST_FLAG", True) is True
    assert recovery_policy.is_feature_flag_enabled("UNIT_TEST_FLAG", False) is False


def test_is_feature_flag_enabled_should_parse_truthy(monkeypatch) -> None:  # noqa: ANN001
    """开关应识别真值字符串。"""

    for raw_value in ("1", "true", "yes", "on", "TRUE"):
        monkeypatch.setenv("UNIT_TEST_FLAG", raw_value)
        assert recovery_policy.is_feature_flag_enabled("UNIT_TEST_FLAG", False) is True


def test_runtime_recovery_default_enabled(monkeypatch) -> None:  # noqa: ANN001
    """ENABLE_RUNTIME_RECOVERY 默认开启。"""

    monkeypatch.delenv("ENABLE_RUNTIME_RECOVERY", raising=False)
    assert recovery_policy.is_runtime_recovery_enabled() is True

    monkeypatch.setenv("ENABLE_RUNTIME_RECOVERY", "false")
    assert recovery_policy.is_runtime_recovery_enabled() is False


def test_plugin_registry_default_disabled(monkeypatch) -> None:  # noqa: ANN001
    """ENABLE_PLUGIN_REGISTRY 默认关闭。"""

    monkeypatch.delenv("ENABLE_PLUGIN_REGISTRY", raising=False)
    assert recovery_policy.is_plugin_registry_enabled() is False

    monkeypatch.setenv("ENABLE_PLUGIN_REGISTRY", "1")
    assert recovery_policy.is_plugin_registry_enabled() is True


def test_is_plugin_registry_error_should_match_hints() -> None:
    """异常关键字命中应返回 True。"""

    assert recovery_policy.is_plugin_registry_error("plugin registry connection failed") is True
    assert recovery_policy.is_plugin_registry_error("插件加载失败") is True
    assert recovery_policy.is_plugin_registry_error("normal business error") is False


def test_should_degrade_on_plugin_failure_requires_two_flags(monkeypatch) -> None:  # noqa: ANN001
    """降级触发需要 recovery 与 plugin_registry 同时开启。"""

    error_text = "plugin_registry init timeout"

    monkeypatch.setenv("ENABLE_RUNTIME_RECOVERY", "0")
    monkeypatch.setenv("ENABLE_PLUGIN_REGISTRY", "1")
    assert recovery_policy.should_degrade_on_plugin_failure(error_text) is False

    monkeypatch.setenv("ENABLE_RUNTIME_RECOVERY", "1")
    monkeypatch.setenv("ENABLE_PLUGIN_REGISTRY", "0")
    assert recovery_policy.should_degrade_on_plugin_failure(error_text) is False

    monkeypatch.setenv("ENABLE_RUNTIME_RECOVERY", "1")
    monkeypatch.setenv("ENABLE_PLUGIN_REGISTRY", "1")
    assert recovery_policy.should_degrade_on_plugin_failure(error_text) is True
