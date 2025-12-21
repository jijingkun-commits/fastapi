"""LLM 流式输出接口（SSE）。"""
import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


router = APIRouter(tags=["llm"])


class ChatRequest(BaseModel):
    """对话请求体。"""
    prompt: str
    delay_ms: int = 50


async def sse_stream(prompt: str, delay_ms: int = 50) -> AsyncGenerator[bytes, None]:
    """将生成内容以 SSE 事件流输出，payload 为 JSON：{"token": "..."}"""
    yield b":ok\n\n"
    for token in prompt.split():
        payload = json.dumps({"token": token}, ensure_ascii=False)
        data = f"data: {payload}\n\n".encode()
        yield data
        await asyncio.sleep(max(delay_ms, 1) / 1000.0)
    yield b"data: [DONE]\n\n"


@router.post("/llm/stream")
async def llm_stream(payload: ChatRequest):
    """流式输出对话内容（SSE）。"""
    gen = sse_stream(payload.prompt, payload.delay_ms)
    return StreamingResponse(gen, media_type="text/event-stream")
