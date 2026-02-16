"""LLM 场景治理调用单元测试。"""

from unittest.mock import MagicMock, patch

import pytest

from app.ai.llm_util import get_llm, get_scene_llm
from app.ai.scene_registry import SCENE_KEY_DATA_INTENT_ANALYSIS


def test_get_llm_requires_model_id():
    """业务侧禁止无场景直接调用 get_llm。"""

    with pytest.raises(ValueError) as exc:
        get_llm()

    assert "get_scene_llm" in str(exc.value)


@patch("app.ai.llm_util.get_llm")
@patch("app.services.llm_scene_service.LLMSceneService.resolve_model_code")
def test_get_scene_llm_uses_scene_service(
    mock_resolve_model_code,
    mock_get_llm,
):
    """get_scene_llm 应通过场景服务解析默认模型。"""

    mock_resolve_model_code.return_value = "sql-scene-model"
    mock_get_llm.return_value = MagicMock()

    get_scene_llm(scene_key=SCENE_KEY_DATA_INTENT_ANALYSIS, internal=True)

    mock_resolve_model_code.assert_called_once_with(
        scene_key=SCENE_KEY_DATA_INTENT_ANALYSIS,
        model_id=None,
    )
    mock_get_llm.assert_called_once_with(model_id="sql-scene-model", internal=True)


@patch("app.ai.llm_util.get_llm")
@patch("app.services.llm_scene_service.LLMSceneService.resolve_model_code")
def test_get_scene_llm_prefers_explicit_model(
    mock_resolve_model_code,
    mock_get_llm,
):
    """显式 model_id 应透传到场景服务做兼容校验。"""

    mock_resolve_model_code.return_value = "manual-model"
    mock_get_llm.return_value = MagicMock()

    get_scene_llm(
        scene_key=SCENE_KEY_DATA_INTENT_ANALYSIS,
        model_id="manual-model",
        internal=True,
    )

    mock_resolve_model_code.assert_called_once_with(
        scene_key=SCENE_KEY_DATA_INTENT_ANALYSIS,
        model_id="manual-model",
    )
    mock_get_llm.assert_called_once_with(model_id="manual-model", internal=True)
