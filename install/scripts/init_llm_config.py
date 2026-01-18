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
