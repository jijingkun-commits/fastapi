#!/usr/bin/env python3
"""测试 LLM 模型配置是否正确。

Usage:
    cd /path/to/fastapi
    python -m scripts.test_llm_config
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI


def test_model(model_code: str, base_url: str, api_key: str, model_name: str = None):
    """测试单个模型是否可用。"""
    print(f"\n{'='*60}")
    print(f"测试模型: {model_name or model_code}")
    print(f"  - model_code: {model_code}")
    print(f"  - base_url: {base_url}")
    print(f"  - api_key: {api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else f"  - api_key: {api_key}")
    print("-" * 60)
    
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        response = client.chat.completions.create(
            model=model_code,
            messages=[{"role": "user", "content": "请回复：测试成功"}],
            max_tokens=50,
            temperature=0
        )
        
        content = response.choices[0].message.content
        print(f"✅ 成功! 模型响应: {content[:100]}")
        return True
        
    except Exception as e:
        print(f"❌ 失败! 错误: {e}")
        return False


def test_from_db():
    """从数据库加载配置并测试所有模型。"""
    print("\n" + "=" * 60)
    print("从数据库加载 LLM 配置...")
    print("=" * 60)
    
    from app.db.session import SessionLocal
    from app.services.llm_config_service import LLMConfigService
    
    with SessionLocal() as db:
        LLMConfigService.load_from_db(db)
    
    # 获取默认 chat 模型
    default_config = LLMConfigService.get_model_by_type("chat")
    if default_config:
        print(f"\n默认 chat 模型: {default_config.model_name} ({default_config.model_code})")
        test_model(
            model_code=default_config.model_code,
            base_url=default_config.base_url,
            api_key=default_config.api_key,
            model_name=default_config.model_name
        )
    else:
        print("❌ 未找到默认 chat 模型!")


def test_specific_models():
    """测试特定模型（不依赖数据库）。"""
    print("\n" + "=" * 60)
    print("测试特定模型配置...")
    print("=" * 60)
    
    # 从环境变量获取 API Keys
    qwen_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    zhipu_key = os.getenv("ZHIPU_API_KEY")
    
    results = []
    
    # 测试阿里云 DashScope - qwen-plus
    if qwen_key:
        results.append(("qwen-plus (阿里云)", test_model(
            model_code="qwen-plus",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=qwen_key,
            model_name="Qwen Plus"
        )))
        
        # 测试 DeepSeek-V3 via DashScope
        results.append(("deepseek-v3 (阿里云)", test_model(
            model_code="deepseek-v3",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=qwen_key,
            model_name="DeepSeek-V3 via DashScope"
        )))
        
        # 测试 DeepSeek-V3.2 via DashScope
        results.append(("deepseek-v3.2 (阿里云)", test_model(
            model_code="deepseek-v3.2",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=qwen_key,
            model_name="DeepSeek-V3.2 via DashScope"
        )))
    else:
        print("\n⚠️  未配置 QWEN_API_KEY 或 DASHSCOPE_API_KEY，跳过阿里云模型测试")
    
    # 测试 DeepSeek 官方 API
    if deepseek_key:
        results.append(("deepseek-chat (官方)", test_model(
            model_code="deepseek-chat",
            base_url="https://api.deepseek.com",
            api_key=deepseek_key,
            model_name="DeepSeek Chat (官方 API)"
        )))
    else:
        print("\n⚠️  未配置 DEEPSEEK_API_KEY，跳过 DeepSeek 官方 API 测试")
    
    # 测试智谱 AI
    if zhipu_key:
        results.append(("glm-4-flash (智谱)", test_model(
            model_code="glm-4-flash",
            base_url="https://open.bigmodel.cn/api/paas/v4",
            api_key=zhipu_key,
            model_name="GLM-4 Flash"
        )))
    else:
        print("\n⚠️  未配置 ZHIPU_API_KEY，跳过智谱模型测试")
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {status} - {name}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="测试 LLM 模型配置")
    parser.add_argument("--db", action="store_true", help="从数据库加载配置测试默认模型")
    parser.add_argument("--all", action="store_true", help="测试所有预配置的模型")
    args = parser.parse_args()
    
    if args.db:
        test_from_db()
    elif args.all:
        test_specific_models()
    else:
        # 默认：先测试数据库配置，再测试特定模型
        test_from_db()
        print("\n\n")
        test_specific_models()


if __name__ == "__main__":
    main()
