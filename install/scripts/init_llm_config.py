"""初始化 LLM 配置数据（中文注释）。

此脚本用于将预定义的模型配置写入数据库。
用法：
    python install/scripts/init_llm_config.py
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.llm_provider import LLMProvider
from app.models.llm_model import LLMModel
from app.core import config

def init_llm_data(db: Session):
    print("开始初始化 LLM 配置...")
    
    # 1. 提供商
    providers_data = [
        {
            "code": "qwen",
            "name": "阿里通义",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": os.getenv("QWEN_API_KEY", ""),
            "sort_order": 1,
            "extra_config": {}
        },
        {
            "code": "deepseek", 
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com",
            "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "sort_order": 2,
            "extra_config": {}
        }
    ]
    
    provider_map = {}
    
    for p_data in providers_data:
        provider = db.query(LLMProvider).filter(LLMProvider.code == p_data["code"]).first()
        if not provider:
            provider = LLMProvider(**p_data)
            db.add(provider)
            print(f"创建提供商: {p_data['name']}")
        else:
            # 更新字段（除了 API Key，如果不想覆盖）
            provider.name = p_data["name"]
            provider.base_url = p_data["base_url"]
            # 如果配置有值，才更新 key
            if p_data["api_key"]:
                provider.api_key = p_data["api_key"]
            print(f"更新提供商: {p_data['name']}")
            
        db.flush() # 获取 ID
        provider_map[p_data["code"]] = provider.id

    # 2. 模型
    models_data = [
        # Qwen
        {
            "provider": "qwen",
            "model_code": "qwen-plus",
            "model_name": "Qwen Plus",
            "supports_thinking": False,
            "is_default": (config.MODEL_PROVIDER == "qwen" and config.MODEL_NAME == "qwen-plus"),
            "extra_config": {}
        },
        {
            "provider": "qwen",
            "model_code": "qwen-max",
            "model_name": "Qwen Max",
            "supports_thinking": False,
            "is_default": (config.MODEL_PROVIDER == "qwen" and config.MODEL_NAME == "qwen-max"),
            "extra_config": {}
        },
        # DeepSeek
        {
            "provider": "deepseek",
            "model_code": "deepseek-chat",
            "model_name": "DeepSeek Chat (V3)",
            "supports_thinking": False,
            "is_default": (config.MODEL_PROVIDER == "deepseek" and config.MODEL_NAME == "deepseek-chat"),
            "extra_config": {}
        },
        {
            "provider": "deepseek",
            "model_code": "deepseek-reasoner",
            "model_name": "DeepSeek Reasoner (R1)",
            "supports_thinking": True,
            "model_type": "reasoning",
            "thinking_budget": 4096,
            "is_default": (config.MODEL_PROVIDER == "deepseek" and config.MODEL_NAME == "deepseek-reasoner"),
            "extra_config": {"effort": "medium"}
        },
        # Kimi (Moonshot AI, via DashScope)
        {
            "provider": "qwen",
            "model_code": "kimi-k2-thinking",
            "model_name": "Kimi K2 Thinking",
            "model_type": "reasoning",
            "supports_thinking": True,
            "supports_tool_call": True,
            "supports_streaming": True,
            "max_output_tokens": 16384,
            "context_window": 262144,
            "default_temperature": 1.0,
            "thinking_budget": 32768,
            "description": "Kimi K2 Thinking（月之暗面）：深度推理模型，基于 MoE 架构（约 1T 总参数 / 32B 激活参数），仅支持思考模式。在编码、数学推理、逻辑分析和工具调用方面表现卓越，适合需要深度理解和多步骤规划的复杂任务。通过阿里云 DashScope 接入。",
            "is_default": False,
            "extra_config": {}
        },
        {
            "provider": "qwen",
            "model_code": "kimi-k2.5",
            "model_name": "Kimi K2.5",
            "model_type": "chat",
            "supports_thinking": True,
            "supports_tool_call": True,
            "supports_streaming": True,
            "max_output_tokens": 32768,
            "context_window": 262144,
            "default_temperature": 0.6,
            "thinking_budget": 32768,
            "description": "Kimi K2.5（月之暗面）：迄今最全能的旗舰模型，在 Agent、代码生成、视觉理解及通用智能任务上取得开源 SOTA 表现。支持图像/视频/文本多模态输入，可切换思考与非思考模式。适合需要综合能力的复杂场景。通过阿里云 DashScope 接入。",
            "is_default": False,
            "extra_config": {}
        }
    ]

    for m_data in models_data:
        provider_code = m_data.pop("provider")
        provider_id = provider_map.get(provider_code)
        
        if not provider_id:
            print(f"警告: 未找到提供商 {provider_code}，跳过模型 {m_data['model_code']}")
            continue
            
        model = db.query(LLMModel).filter(
            LLMModel.provider_id == provider_id,
            LLMModel.model_code == m_data["model_code"]
        ).first()
        
        if not model:
            model = LLMModel(provider_id=provider_id, **m_data)
            db.add(model)
            print(f"创建模型: {m_data['model_name']}")
        else:
            # 更新除了 id/provider_id 外的字段
            for k, v in m_data.items():
                setattr(model, k, v)
            print(f"更新模型: {m_data['model_name']}")

    db.commit()
    print("LLM 配置初始化完成！")

if __name__ == "__main__":
    with SessionLocal() as db:
        init_llm_data(db)
