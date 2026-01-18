"""LLM 配置相关的 Pydantic 模型（中文注释）。"""
from typing import Optional
from pydantic import BaseModel, ConfigDict


class LLMProviderOut(BaseModel):
    """提供商输出模型。"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    code: str
    name: str
    base_url: Optional[str] = None
    is_active: bool


class LLMModelOut(BaseModel):
    """模型输出模型（供前端下拉选择）。"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    model_code: str
    model_name: str
    model_type: str
    supports_thinking: bool
    supports_tool_call: bool
    description: Optional[str] = None
    is_default: bool
    provider_id: int
    
    # 扁平化提供商信息（可选，如果需要）
    # provider_name: str


class LLMModelConfig(BaseModel):
    """模型完整配置（内部使用，包含敏感信息）。"""
    model_config = ConfigDict(from_attributes=True)
    
    model_code: str
    model_name: str
    model_type: str = "chat"  # chat/vision/embedding/rerank/asr/tts
    provider_code: str
    base_url: Optional[str]
    api_key: Optional[str]
    temperature: float
    supports_thinking: bool
    thinking_budget: int
    max_output_tokens: int
    context_window: int
    extra_config: Optional[dict] = None

