#!/usr/bin/env python3
"""wtimp dispatch bridge for cardrun.

负责把 cardrun dispatch 阶段升级为“真实执行 wtimp + 结构化结果回传”。
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 1800
DEFAULT_SANDBOX = "workspace-write"


class WtimpDispatchError(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass(eq=True)
class WtimpDispatchRequest:
    task_key: str
    card_id: str
    ws_file: str
    worktree_path: str
    executor_mode: str
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    sandbox: str = DEFAULT_SANDBOX


@dataclass(eq=True)
class WtimpDispatchResult:
    ok: bool
    executor: str
    executor_mode: str
    card_id: str
    ws_file: str
    subagent_id: str | None
    commit_sha: str | None
    merge_sha: str | None
    changed_files: list[str]
    acceptance_results: list[dict[str, Any]]
    worktree_path: str
    error_code: str | None = None
    error_message: str | None = None


def build_wtimp_prompt(request: WtimpDispatchRequest) -> str:
    return (
        "你正在执行 cardrun 的 wtimp dispatch bridge。\n"
        f"任务 task_key={request.task_key}，当前卡 card_id={request.card_id}。\n"
        f"必须在当前工作目录内执行 `$jjk-wtimp @{request.ws_file}`，并使用 `executor_mode=cardrun_dispatch`。\n"
        "禁止 create worktree，禁止 merge，禁止输出解释文本。\n"
        "完成后只输出一段 JSON，对象字段至少包含："
        "ok, executor, executor_mode, card_id, ws_file, subagent_id, commit_sha, merge_sha, changed_files, acceptance_results, error_code, error_message。\n"
        f"其中 executor 必须是 `wtimp`，executor_mode 必须是 `{request.executor_mode}`，"
        f"card_id 必须是 `{request.card_id}`，ws_file 必须是 `{request.ws_file}`。"
    )


def build_codex_exec_command(request: WtimpDispatchRequest) -> list[str]:
    return [
        "codex",
        "-a",
        "never",
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        request.sandbox,
        build_wtimp_prompt(request),
    ]


def _extract_last_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    candidate: dict[str, Any] | None = None
    fallback: dict[str, Any] | None = None
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if fallback is None:
            fallback = payload
        if any(key in payload for key in ("ok", "executor", "card_id", "ws_file", "commit_sha")):
            candidate = payload
    if candidate is not None:
        return candidate
    if fallback is None:
        raise WtimpDispatchError(
            "CARDRUN_EXECUTION_RESULT_INVALID",
            "wtimp dispatch 未返回可解析 JSON",
            {"stdout_preview": text[:500]},
        )
    return fallback


def _normalize_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for item in values:
        value = str(item or "").strip()
        if value:
            result.append(value)
    return result


def _normalize_dict_list(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, dict)]


def _validate_payload(request: WtimpDispatchRequest, payload: dict[str, Any]) -> WtimpDispatchResult:
    executor = str(payload.get("executor") or "").strip().lower()
    executor_mode = str(payload.get("executor_mode") or "").strip().lower()
    card_id = str(payload.get("card_id") or "").strip().upper()
    ws_file = str(payload.get("ws_file") or "").strip()
    commit_sha = str(payload.get("commit_sha") or "").strip() or None
    merge_sha = str(payload.get("merge_sha") or "").strip() or None
    subagent_id = str(payload.get("subagent_id") or "").strip() or None

    if not bool(payload.get("ok")):
        raise WtimpDispatchError(
            "CARDRUN_SUBAGENT_FAILED",
            str(payload.get("error_message") or "wtimp dispatch 返回失败结果"),
            {
                "card_id": request.card_id,
                "ws_file": request.ws_file,
                "downstream_error_code": str(payload.get("error_code") or "").strip() or None,
                "downstream_error_message": str(payload.get("error_message") or "").strip() or None,
            },
        )

    if executor != "wtimp":
        raise WtimpDispatchError(
            "CARDRUN_EXECUTION_RESULT_INVALID",
            f"wtimp dispatch executor 非法: {executor or 'missing'}",
            {"expected": "wtimp", "actual": executor or "missing", "card_id": request.card_id},
        )
    if executor_mode != request.executor_mode:
        raise WtimpDispatchError(
            "CARDRUN_EXECUTION_RESULT_INVALID",
            f"wtimp dispatch executor_mode 非法: {executor_mode or 'missing'}",
            {"expected": request.executor_mode, "actual": executor_mode or "missing", "card_id": request.card_id},
        )
    if card_id != request.card_id:
        raise WtimpDispatchError(
            "CARDRUN_EXECUTION_RESULT_INVALID",
            f"wtimp dispatch card_id 不匹配: {card_id or 'missing'}",
            {"expected": request.card_id, "actual": card_id or "missing", "ws_file": request.ws_file},
        )
    if ws_file != request.ws_file:
        raise WtimpDispatchError(
            "CARDRUN_EXECUTION_RESULT_INVALID",
            f"wtimp dispatch ws_file 不匹配: {ws_file or 'missing'}",
            {"expected": request.ws_file, "actual": ws_file or "missing", "card_id": request.card_id},
        )
    if not commit_sha:
        raise WtimpDispatchError(
            "CARDRUN_NO_COMMIT_EVIDENCE",
            f"card_id={request.card_id} dispatch 缺少 commit_sha 证据",
            {"card_id": request.card_id, "ws_file": request.ws_file},
        )

    return WtimpDispatchResult(
        ok=True,
        executor="wtimp",
        executor_mode=request.executor_mode,
        card_id=request.card_id,
        ws_file=request.ws_file,
        subagent_id=subagent_id,
        commit_sha=commit_sha,
        merge_sha=merge_sha,
        changed_files=_normalize_string_list(payload.get("changed_files")),
        acceptance_results=_normalize_dict_list(payload.get("acceptance_results")),
        worktree_path=request.worktree_path,
        error_code=str(payload.get("error_code") or "").strip() or None,
        error_message=str(payload.get("error_message") or "").strip() or None,
    )


def run_dispatch(request: WtimpDispatchRequest) -> WtimpDispatchResult:
    command = build_codex_exec_command(request)
    try:
        completed = subprocess.run(
            command,
            cwd=str(Path(request.worktree_path).resolve()),
            capture_output=True,
            text=True,
            timeout=request.timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise WtimpDispatchError(
            "CARDRUN_SUBAGENT_FAILED",
            "未找到 codex 命令，无法执行 wtimp dispatch",
            {"card_id": request.card_id, "worktree_path": request.worktree_path},
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise WtimpDispatchError(
            "CARDRUN_SUBAGENT_FAILED",
            f"wtimp dispatch 执行超时: {request.timeout_seconds}s",
            {
                "card_id": request.card_id,
                "worktree_path": request.worktree_path,
                "timeout_seconds": request.timeout_seconds,
                "stdout_preview": str(exc.stdout or "")[:500],
                "stderr_preview": str(exc.stderr or "")[:500],
            },
        ) from exc

    if completed.returncode != 0:
        raise WtimpDispatchError(
            "CARDRUN_SUBAGENT_FAILED",
            f"wtimp dispatch 执行失败: exit_code={completed.returncode}",
            {
                "card_id": request.card_id,
                "ws_file": request.ws_file,
                "exit_code": completed.returncode,
                "stdout_preview": str(completed.stdout or "")[:500],
                "stderr_preview": str(completed.stderr or "")[:500],
                "command": command,
            },
        )

    payload = _extract_last_json_object(str(completed.stdout or ""))
    return _validate_payload(request, payload)
