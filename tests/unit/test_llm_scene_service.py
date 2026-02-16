"""LLM 场景治理服务单元测试。"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.llm_scene_service import (
    LLMSceneService,
    SceneConfigError,
    SceneRuntimeConfig,
)


def _scene(
    key: str,
    *,
    scene_type: str = "text",
    model_code: str = "qwen-plus",
    model_type: str = "chat",
    is_active: bool = True,
) -> SceneRuntimeConfig:
    return SceneRuntimeConfig(
        scene_key=key,
        scene_name=key,
        scene_type=scene_type,
        default_model_id=1,
        default_model_code=model_code,
        default_model_type=model_type,
        is_active=is_active,
        description=None,
    )


def test_validate_startup_integrity_fails_when_scene_missing():
    """启动校验应拦截缺失场景。"""

    old_cache = LLMSceneService._scene_cache
    old_initialized = LLMSceneService._initialized

    LLMSceneService._scene_cache = {
        "app.ai.intent_classifier.classify_intent": _scene("app.ai.intent_classifier.classify_intent"),
    }
    LLMSceneService._initialized = True

    try:
        with pytest.raises(SceneConfigError) as exc:
            LLMSceneService.validate_startup_integrity(
                required_scene_keys={
                    "app.ai.intent_classifier.classify_intent",
                    "app.ai.workflow.data_graph.analyze_data_intent",
                }
            )
        assert "缺失场景配置" in str(exc.value)
    finally:
        LLMSceneService._scene_cache = old_cache
        LLMSceneService._initialized = old_initialized


def test_resolve_model_code_checks_scene_status():
    """停用场景不允许被解析。"""

    old_cache = LLMSceneService._scene_cache
    old_initialized = LLMSceneService._initialized

    LLMSceneService._scene_cache = {
        "app.ai.intent_classifier.classify_intent": _scene(
            "app.ai.intent_classifier.classify_intent",
            is_active=False,
        ),
    }
    LLMSceneService._initialized = True

    try:
        with pytest.raises(SceneConfigError) as exc:
            LLMSceneService.resolve_model_code("app.ai.intent_classifier.classify_intent")
        assert "场景已停用" in str(exc.value)
    finally:
        LLMSceneService._scene_cache = old_cache
        LLMSceneService._initialized = old_initialized


@patch("app.services.llm_scene_service.LLMConfigService.get_model_config")
def test_resolve_model_code_validates_model_type(mock_get_model_config):
    """场景类型与模型类型不兼容时应报错。"""

    old_cache = LLMSceneService._scene_cache
    old_initialized = LLMSceneService._initialized

    LLMSceneService._scene_cache = {
        "app.ai.intent_classifier.classify_intent": _scene(
            "app.ai.intent_classifier.classify_intent",
            scene_type="embedding",
            model_code="qwen-plus",
        ),
    }
    LLMSceneService._initialized = True

    mock_get_model_config.return_value = SimpleNamespace(
        model_code="qwen-plus",
        model_type="chat",
    )

    try:
        with pytest.raises(SceneConfigError) as exc:
            LLMSceneService.resolve_model_code("app.ai.intent_classifier.classify_intent")
        assert "类型不兼容" in str(exc.value)
    finally:
        LLMSceneService._scene_cache = old_cache
        LLMSceneService._initialized = old_initialized
