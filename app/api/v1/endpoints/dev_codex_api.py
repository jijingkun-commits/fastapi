"""开发工具 API：桥接本机 Codex CLI（仅开发/测试环境）。"""

from __future__ import annotations

import shlex
import subprocess
import time
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core import config as core_config


router = APIRouter(prefix="/dev-tools", tags=["开发工具（仅开发环境）"])


class CodexExecRequest(BaseModel):
    """Codex 执行请求。"""

    prompt: str = Field(..., min_length=1, max_length=8000)
    model: Optional[str] = Field(default=None, max_length=100)
    sandbox: Literal["read-only", "workspace-write", "danger-full-access"] = "read-only"
    timeout_sec: int = Field(default=180, ge=10, le=1800)
    working_dir: Optional[str] = None


class CodexExecResponse(BaseModel):
    """Codex 执行结果。"""

    ok: bool
    exit_code: int
    duration_ms: int
    stdout: str
    stderr: str
    command: str
    workdir: str
    dev_only: bool = True


def _ensure_dev_environment() -> None:
    """限制仅开发/测试环境可调用。"""

    if core_config.ENV == "prod":
        raise HTTPException(status_code=403, detail="该接口仅允许在开发/测试环境使用")


def _resolve_workdir(working_dir: Optional[str]) -> str:
    """解析并校验执行目录，必须位于项目目录内。"""

    project_root = core_config.PROJECT_ROOT.resolve()
    if not working_dir:
        return str(project_root)

    candidate = Path(working_dir).expanduser().resolve()
    if candidate != project_root and project_root not in candidate.parents:
        raise HTTPException(status_code=400, detail="working_dir 必须位于项目目录内")

    return str(candidate)


def _build_codex_command(request: CodexExecRequest) -> list[str]:
    """构造 codex exec 命令。"""

    command = ["codex", "-a", "never"]
    if request.model and request.model.strip():
        command.extend(["-m", request.model.strip()])
    command.extend(
        [
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            request.sandbox,
            request.prompt,
        ]
    )
    return command


def _clip_text(value: str, limit: int = 16000) -> str:
    """裁剪命令输出，避免响应体过大。"""

    if len(value) <= limit:
        return value
    return value[:limit] + "\n...[输出已截断]"


def _safe_text(value) -> str:
    """规范化 subprocess 输出。"""

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


@router.post("/codex/exec", response_model=CodexExecResponse)
def run_codex_exec(request: CodexExecRequest) -> CodexExecResponse:
    """执行本机 codex 命令。"""

    _ensure_dev_environment()
    workdir = _resolve_workdir(request.working_dir)
    command = _build_codex_command(request)

    start_time = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=request.timeout_sec,
            check=False,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="未找到 codex 命令，请先安装 Codex CLI") from exc
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return CodexExecResponse(
            ok=False,
            exit_code=124,
            duration_ms=duration_ms,
            stdout=_clip_text(_safe_text(exc.stdout)),
            stderr=_clip_text(_safe_text(exc.stderr) + f"\n执行超时：{request.timeout_sec}s"),
            command=" ".join(shlex.quote(part) for part in command),
            workdir=workdir,
        )

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    return CodexExecResponse(
        ok=completed.returncode == 0,
        exit_code=completed.returncode,
        duration_ms=duration_ms,
        stdout=_clip_text(_safe_text(completed.stdout)),
        stderr=_clip_text(_safe_text(completed.stderr)),
        command=" ".join(shlex.quote(part) for part in command),
        workdir=workdir,
    )
