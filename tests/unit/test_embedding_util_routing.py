"""Embedding 工具路由配置单元测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.ai.utils import embedding_util
from app.services.llm_scene_service import SceneConfigError


@patch(
    "app.ai.utils.embedding_util.LLMSceneService.resolve_model_code",
    side_effect=SceneConfigError("场景未配置"),
)
def test_get_embedding_returns_none_when_scene_missing(_mock_resolve_scene_model):
    """Embedding 场景未配置时应直接返回 None。"""

    result = embedding_util.get_embedding("hello")
    assert result is None


@patch("app.ai.utils.embedding_util.OpenAI")
@patch("app.ai.utils.embedding_util.LLMConfigService.get_model_config")
@patch(
    "app.ai.utils.embedding_util.LLMSceneService.resolve_model_code",
    return_value="embedding-3",
)
def test_get_embedding_uses_scene_binding_model(
    mock_resolve_scene_model,
    mock_get_model_config,
    mock_openai,
):
    """Embedding 生成应使用场景绑定解析出的模型代码。"""

    mock_get_model_config.return_value = SimpleNamespace(
        model_code="embedding-3",
        model_name="Embedding-3",
        api_key="test-key",
        base_url="https://example.com/v1",
    )
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.0] * embedding_util.EMBEDDING_DIMENSION)],
    )
    mock_openai.return_value = mock_client

    result = embedding_util.get_embedding("hello")

    assert isinstance(result, list)
    assert len(result) == embedding_util.EMBEDDING_DIMENSION
    mock_resolve_scene_model.assert_called_once_with(
        "app.ai.utils.embedding_util.get_embedding",
        model_id=None,
    )
    mock_get_model_config.assert_called_once_with("embedding-3")
    mock_client.embeddings.create.assert_called_once_with(
        model="embedding-3",
        input="hello",
    )

