"""测试 LLM 配置服务（中文注释）。"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.llm_config_service import LLMConfigService

def test_config_service_initialization():
    """测试服务初始化与缓存加载。"""
    # Mock Repository return values
    mock_provider = MagicMock()
    mock_provider.code = "test_provider"
    mock_provider.api_key = "test_key"
    mock_provider.base_url = "http://test.com"
    
    mock_model = MagicMock()
    mock_model.model_code = "test_model"
    mock_model.model_name = "Test Model"
    mock_model.model_type = "chat"
    mock_model.provider = mock_provider
    mock_model.default_temperature = 0.5
    mock_model.extra_config = {}
    mock_model.supports_thinking = False
    mock_model.thinking_budget = 0
    mock_model.max_output_tokens = 4096
    mock_model.context_window = 4096
    
    mock_provider.name = "Test Provider"
    mock_provider.extra_config = {}
    
    with patch("app.repositories.llm_repo.get_active_providers", return_value=[mock_provider]), \
         patch("app.repositories.llm_repo.get_active_models", return_value=[mock_model]):
        
        LLMConfigService.load_from_db(MagicMock())
        
        # Verify cache
        config = LLMConfigService.get_model_config("test_model")
        assert config is not None
        assert config.provider_code == "test_provider"
        assert config.api_key == "test_key"
        assert config.temperature == 0.5
