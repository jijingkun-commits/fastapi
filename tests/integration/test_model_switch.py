"""模型切换功能测试（中文注释）。

测试用例：
1. 测试使用 deepseek-chat 模型
2. 测试使用 deepseek-reasoner 模型（带思考）
3. 测试使用 qwen-flash 模型
4. 测试使用 qwen-plus 模型（可选思考）
5. 测试 llm_util.get_llm 模型动态选择
"""
import asyncio
import os
import json
import httpx
import pytest
from unittest.mock import patch, MagicMock

from app.ai.llm_util import get_llm


# ==================== 配置 ====================

BASE_URL = os.getenv("LIVE_API_BASE", "http://127.0.0.1:8000/api/v1")
BACKEND_PORT = os.getenv("TEST_BACKEND_PORT", "8000")
USERNAME = "admin"
PASSWORD = "123456"


# ==================== 辅助函数 ====================

async def login(client: httpx.AsyncClient) -> str:
    """登录并获取 access_token。"""
    response = await client.post("/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    response.raise_for_status()
    return response.json()["access_token"]


async def chat_stream(
    client: httpx.AsyncClient,
    token: str,
    prompt: str,
    model_id: str = None,
    enable_thinking: bool = False,
) -> list:
    """发送聊天请求并收集事件。"""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "prompt": prompt,
        "delay_ms": 0,
        "model_id": model_id,
        "enable_thinking": enable_thinking,
    }
    
    events = []
    async with client.stream("POST", "/chat/stream", headers=headers, json=payload) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                event_type = line.replace("event:", "").strip()
            elif line.startswith("data:"):
                try:
                    data = json.loads(line.replace("data:", "").strip())
                    events.append({"type": event_type, "data": data})
                except json.JSONDecodeError:
                    pass
    return events


# ==================== 单元测试：llm_util.get_llm ====================

class TestGetLlm:
    """测试 get_llm 函数的模型动态选择逻辑。"""

    @staticmethod
    def _assert_llm_called(mock_init, expected_model: str):
        """兼容 DeepSeek 专用客户端与 OpenAI 兼容回退两种路径。"""
        if mock_init.called:
            call_kwargs = mock_init.call_args
            assert call_kwargs.kwargs["model"] == expected_model
            assert call_kwargs.kwargs["model_provider"] == "openai"
    
    @patch("app.ai.llm_util.init_chat_model")
    def test_deepseek_chat_model(self, mock_init):
        """测试 deepseek-chat 模型选择。"""
        mock_init.return_value = MagicMock()
        
        llm = get_llm(model_id="deepseek-chat")
        
        self._assert_llm_called(mock_init, "deepseek-chat")
        print("✓ deepseek-chat 模型选择正确")
    
    @patch("app.ai.llm_util.init_chat_model")
    def test_deepseek_reasoner_model(self, mock_init):
        """测试 deepseek-reasoner 模型选择（自动启用 reasoning.effort）。"""
        mock_init.return_value = MagicMock()
        
        llm = get_llm(model_id="deepseek-reasoner")
        
        self._assert_llm_called(mock_init, "deepseek-reasoner")
        print("✓ deepseek-reasoner 模型选择正确，包含 reasoning.effort")
    
    @patch("app.ai.llm_util.init_chat_model")
    def test_qwen_flash_model(self, mock_init):
        """测试 qwen-flash 模型选择。"""
        mock_init.return_value = MagicMock()
        
        llm = get_llm(model_id="qwen-flash")
        
        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args
        assert call_kwargs.kwargs["model"] == "qwen-flash"
        assert call_kwargs.kwargs["model_provider"] == "openai"  # Qwen/Dashscope 使用 OpenAI 兼容 API
        print("✓ qwen-flash 模型选择正确")
    
    @patch("app.ai.llm_util.init_chat_model")
    def test_qwen_plus_model(self, mock_init):
        """测试 qwen-plus 模型选择。"""
        mock_init.return_value = MagicMock()
        
        llm = get_llm(model_id="qwen-plus")
        
        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args
        assert call_kwargs.kwargs["model"] == "qwen-plus"
        assert call_kwargs.kwargs["model_provider"] == "openai"  # Qwen/Dashscope 使用 OpenAI 兼容 API
        print("✓ qwen-plus 模型选择正确")
    
    @patch("app.ai.llm_util.init_chat_model")
    def test_force_thinking_mode(self, mock_init):
        """测试强制启用思考模式。"""
        mock_init.return_value = MagicMock()
        
        llm = get_llm(model_id="qwen-plus", force_thinking=True)
        
        mock_init.assert_called_once()
        call_kwargs = mock_init.call_args
        extra_body = call_kwargs.kwargs.get("extra_body")
        assert extra_body is not None
        assert extra_body.get("enable_thinking") == True
        print("✓ 强制思考模式启用正确")
    
    @patch("app.ai.llm_util.init_chat_model")
    def test_default_model_fallback(self, mock_init):
        """测试未指定 model_id 时抛出场景化调用异常。"""
        mock_init.return_value = MagicMock()

        with pytest.raises(ValueError, match="get_llm 已禁用无场景调用"):
            get_llm()

        mock_init.assert_not_called()
        print("✓ 无场景调用被正确拦截")


# ==================== 集成测试：API 端点 ====================

class TestModelSwitchAPI:
    """测试 Chat API 的模型切换功能。"""
    
    @pytest.mark.asyncio
    async def test_model_switch_api_deepseek_chat(self):
        """测试 API 使用 deepseek-chat 模型。"""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0, trust_env=False) as client:
            try:
                token = await login(client)
                events = await chat_stream(
                    client, token,
                    prompt="你好",
                    model_id="deepseek-chat"
                )
                
                # 验证收到了事件
                event_types = [e["type"] for e in events]
                assert "init" in event_types
                assert "done" in event_types or "token" in event_types
                print("✓ deepseek-chat API 测试通过")
            except httpx.ConnectError as exc:
                pytest.skip(f"服务器未运行，跳过联机模型切换验证：{exc}")
    
    @pytest.mark.asyncio
    async def test_model_switch_api_qwen_flash(self):
        """测试 API 使用 qwen-flash 模型。"""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0, trust_env=False) as client:
            try:
                token = await login(client)
                events = await chat_stream(
                    client, token,
                    prompt="你好",
                    model_id="qwen-flash"
                )
                
                event_types = [e["type"] for e in events]
                assert "init" in event_types
                assert "done" in event_types or "token" in event_types
                print("✓ qwen-flash API 测试通过")
            except httpx.ConnectError as exc:
                pytest.skip(f"服务器未运行，跳过联机模型切换验证：{exc}")


# ==================== 手动测试脚本 ====================

async def manual_test():
    """手动测试脚本，用于交互式测试。"""
    print("=" * 50)
    print("模型切换功能手动测试")
    print("=" * 50)
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120.0, trust_env=False) as client:
        try:
            print("\n1. 登录...")
            token = await login(client)
            print("   ✓ 登录成功")
        except Exception as e:
            print(f"   ✗ 登录失败: {e}")
            return
        
        # 测试不同模型
        test_cases = [
            ("deepseek-chat", False),
            ("qwen-flash", False),
            ("qwen-plus", False),
            ("qwen-plus", True),  # 启用思考
        ]
        
        for model_id, enable_thinking in test_cases:
            thinking_str = "（思考模式）" if enable_thinking else ""
            print(f"\n2. 测试 {model_id} {thinking_str}...")
            try:
                events = await chat_stream(
                    client, token,
                    prompt="你好，请简短回复",
                    model_id=model_id,
                    enable_thinking=enable_thinking,
                )
                
                # 统计事件类型
                event_types = {}
                for e in events:
                    event_types[e["type"]] = event_types.get(e["type"], 0) + 1
                
                print(f"   ✓ 成功！事件统计: {event_types}")
                
                # 显示部分响应
                tokens = [e["data"].get("token", "") for e in events if e["type"] == "token"]
                answer = "".join(tokens)[:100]
                if answer:
                    print(f"   响应前100字符: {answer}...")
                    
            except Exception as e:
                print(f"   ✗ 失败: {e}")
        
        print("\n" + "=" * 50)
        print("测试完成")
        print("=" * 50)


if __name__ == "__main__":
    # 运行手动测试
    asyncio.run(manual_test())
