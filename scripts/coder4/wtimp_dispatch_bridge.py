#!/usr/bin/env python3
"""wtimp dispatch bridge for cardrun.

负责把 cardrun dispatch 阶段升级为“真实执行 wtimp + 结构化结果回传”。
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 1800
DEFAULT_SANDBOX = "workspace-write"
PREVIEW_LIMIT = 500
DISPATCH_RESULT_REQUIRED_KEYS = frozenset(
    {
        "ok",
        "executor",
        "executor_mode",
        "card_id",
        "ws_file",
        "subagent_id",
        "commit_sha",
        "merge_sha",
        "changed_files",
        "acceptance_results",
        "evidence_satisfied",
    }
)


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
    evidence_satisfied: bool
    worktree_path: str
    error_code: str | None = None
    error_message: str | None = None


def build_wtimp_prompt(request: WtimpDispatchRequest) -> str:
    return (
        "你正在执行 cardrun 的 wtimp dispatch bridge。\n"
        f"任务 task_key={request.task_key}，当前卡 card_id={request.card_id}。\n"
        f"必须在当前工作目录内执行 `$jjk-wtimp @{request.ws_file}`，并使用 `executor_mode=cardrun_dispatch`。\n"
        "禁止 create worktree，禁止 merge，禁止输出解释文本。\n"
        "acceptance_results[*] 必须包含 kind/cmd/exit_code/summary。\n"
        "完成后只输出一段 JSON，对象字段至少包含："
        "ok, executor, executor_mode, card_id, ws_file, subagent_id, commit_sha, merge_sha, changed_files, acceptance_results, evidence_satisfied, error_code, error_message。\n"
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


def _preview_text(value: Any) -> str:
    return str(value or "")[:PREVIEW_LIMIT]


def _iter_json_objects(text: str):
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        yield payload


def _is_dispatch_result_payload(payload: dict[str, Any]) -> bool:
    return DISPATCH_RESULT_REQUIRED_KEYS.issubset(payload.keys())


def _extract_dispatch_result_payload(text: str) -> dict[str, Any]:
    matched_payloads = [payload for payload in _iter_json_objects(text) if _is_dispatch_result_payload(payload)]
    if len(matched_payloads) == 1:
        return matched_payloads[0]
    if not matched_payloads:
        raise WtimpDispatchError(
            "CARDRUN_EXECUTION_RESULT_INVALID",
            "wtimp dispatch 未返回符合 contract 的 JSON",
            {"stdout_preview": _preview_text(text), "matched_payload_count": 0},
        )
    raise WtimpDispatchError(
        "CARDRUN_EXECUTION_RESULT_INVALID",
        "wtimp dispatch 返回多个候选 JSON 结果对象",
        {"stdout_preview": _preview_text(text), "matched_payload_count": len(matched_payloads)},
    )


def _normalize_string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        raise WtimpDispatchError(
            "CARDRUN_EXECUTION_RESULT_INVALID",
            "wtimp dispatch changed_files 类型非法",
            {"field": "changed_files", "actual_type": type(values).__name__},
        )
    result: list[str] = []
    for item in values:
        if not isinstance(item, str):
            raise WtimpDispatchError(
                "CARDRUN_EXECUTION_RESULT_INVALID",
                "wtimp dispatch changed_files 元素类型非法",
                {"field": "changed_files", "actual_type": type(item).__name__},
            )
        value = item.strip()
        if value:
            result.append(value)
    return result


def _normalize_acceptance_results(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        raise WtimpDispatchError(
            "CARDRUN_EXECUTION_RESULT_INVALID",
            "wtimp dispatch acceptance_results 类型非法",
            {"field": "acceptance_results", "actual_type": type(values).__name__},
        )
    result: list[dict[str, Any]] = []
    for item in values:
        if not isinstance(item, dict):
            raise WtimpDispatchError(
                "CARDRUN_EXECUTION_RESULT_INVALID",
                "wtimp dispatch acceptance_results 元素类型非法",
                {"field": "acceptance_results", "actual_type": type(item).__name__},
            )
        kind = str(item.get("kind") or "").strip().lower()
        cmd = str(item.get("cmd") or "").strip()
        exit_code = item.get("exit_code")
        summary = str(item.get("summary") or "").strip()
        if not kind or not cmd or summary == "":
            raise WtimpDispatchError(
                "CARDRUN_EXECUTION_RESULT_INVALID",
                "wtimp dispatch acceptance_results 缺少必填字段",
                {
                    "field": "acceptance_results",
                    "item": item,
                    "required": ["kind", "cmd", "exit_code", "summary"],
                },
            )
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            raise WtimpDispatchError(
                "CARDRUN_EXECUTION_RESULT_INVALID",
                "wtimp dispatch acceptance_results.exit_code 类型非法",
                {"field": "acceptance_results.exit_code", "actual_type": type(exit_code).__name__},
            )
        result.append(
            {
                "kind": kind,
                "cmd": cmd,
                "exit_code": int(exit_code),
                "summary": summary,
            }
        )
    return result


def _require_string(payload: dict[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str):
        raise WtimpDispatchError(
            "CARDRUN_EXECUTION_RESULT_INVALID",
            f"wtimp dispatch {field_name} 类型非法",
            {"field": field_name, "actual_type": type(value).__name__},
        )
    return value.strip()


def _require_string_or_none(payload: dict[str, Any], field_name: str) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise WtimpDispatchError(
            "CARDRUN_EXECUTION_RESULT_INVALID",
            f"wtimp dispatch {field_name} 类型非法",
            {"field": field_name, "actual_type": type(value).__name__},
        )
    normalized = value.strip()
    return normalized or None


def _require_bool(payload: dict[str, Any], field_name: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise WtimpDispatchError(
            "CARDRUN_EXECUTION_RESULT_INVALID",
            f"wtimp dispatch {field_name} 类型非法",
            {"field": field_name, "actual_type": type(value).__name__},
        )
    return value


def _cleanup_process_group(process: Any) -> dict[str, Any]:
    pgid = int(getattr(process, "pid", 0) or 0)
    details: dict[str, Any] = {
        "attempted": pgid > 0,
        "pgid": pgid or None,
        "signals": [],
        "result": "skipped" if pgid <= 0 else "pending",
    }
    if pgid <= 0:
        return details

    try:
        os.killpg(pgid, signal.SIGTERM)
        details["signals"].append("SIGTERM")
        process.wait(timeout=5)
        details["result"] = "terminated"
        details["returncode"] = getattr(process, "returncode", None)
        return details
    except ProcessLookupError:
        details["result"] = "already_gone"
        return details
    except subprocess.TimeoutExpired:
        try:
            os.killpg(pgid, signal.SIGKILL)
            details["signals"].append("SIGKILL")
            process.wait(timeout=1)
            details["result"] = "killed"
            details["returncode"] = getattr(process, "returncode", None)
            return details
        except ProcessLookupError:
            details["result"] = "already_gone"
            return details
        except Exception as exc:  # noqa: BLE001
            details["result"] = "kill_failed"
            details["error"] = str(exc)
            return details
    except Exception as exc:  # noqa: BLE001
        details["result"] = "cleanup_failed"
        details["error"] = str(exc)
        return details


def _with_session_cleanup(details: dict[str, Any], process: Any, *, stdout: str = "", stderr: str = "") -> dict[str, Any]:
    payload = dict(details)
    if stdout:
        payload.setdefault("stdout_preview", _preview_text(stdout))
    if stderr:
        payload.setdefault("stderr_preview", _preview_text(stderr))
    payload["session_cleanup"] = _cleanup_process_group(process)
    return payload


def _validate_payload(request: WtimpDispatchRequest, payload: dict[str, Any]) -> WtimpDispatchResult:
    ok = _require_bool(payload, "ok")
    executor = _require_string(payload, "executor").lower()
    executor_mode = _require_string(payload, "executor_mode").lower()
    card_id = _require_string(payload, "card_id").upper()
    ws_file = _require_string(payload, "ws_file")
    commit_sha = _require_string_or_none(payload, "commit_sha")
    merge_sha = _require_string_or_none(payload, "merge_sha")
    subagent_id = _require_string_or_none(payload, "subagent_id")
    changed_files = _normalize_string_list(payload.get("changed_files"))
    acceptance_results = _normalize_acceptance_results(payload.get("acceptance_results"))
    evidence_satisfied = _require_bool(payload, "evidence_satisfied")
    error_code = _require_string_or_none(payload, "error_code")
    error_message = _require_string_or_none(payload, "error_message")

    if not ok:
        raise WtimpDispatchError(
            "CARDRUN_SUBAGENT_FAILED",
            error_message or "wtimp dispatch 返回失败结果",
            {
                "card_id": request.card_id,
                "ws_file": request.ws_file,
                "downstream_error_code": error_code,
                "downstream_error_message": error_message,
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
        changed_files=changed_files,
        acceptance_results=acceptance_results,
        evidence_satisfied=evidence_satisfied,
        worktree_path=request.worktree_path,
        error_code=error_code,
        error_message=error_message,
    )


def run_dispatch(request: WtimpDispatchRequest) -> WtimpDispatchResult:
    command = build_codex_exec_command(request)
    try:
        process = subprocess.Popen(
            command,
            cwd=str(Path(request.worktree_path).resolve()),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError as exc:
        raise WtimpDispatchError(
            "CARDRUN_SUBAGENT_FAILED",
            "未找到 codex 命令，无法执行 wtimp dispatch",
            {"card_id": request.card_id, "worktree_path": request.worktree_path},
        ) from exc

    stdout = ""
    stderr = ""
    try:
        stdout, stderr = process.communicate(timeout=request.timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        stdout = str(getattr(exc, "output", None) or getattr(exc, "stdout", None) or "")
        stderr = str(getattr(exc, "stderr", None) or "")
        raise WtimpDispatchError(
            "CARDRUN_SUBAGENT_FAILED",
            f"wtimp dispatch 执行超时: {request.timeout_seconds}s",
            _with_session_cleanup(
                {
                    "card_id": request.card_id,
                    "worktree_path": request.worktree_path,
                    "timeout_seconds": request.timeout_seconds,
                },
                process,
                stdout=stdout,
                stderr=stderr,
            ),
        ) from exc

    if int(process.returncode or 0) != 0:
        raise WtimpDispatchError(
            "CARDRUN_SUBAGENT_FAILED",
            f"wtimp dispatch 执行失败: exit_code={process.returncode}",
            _with_session_cleanup(
                {
                    "card_id": request.card_id,
                    "ws_file": request.ws_file,
                    "exit_code": process.returncode,
                    "command": command,
                },
                process,
                stdout=stdout,
                stderr=stderr,
            ),
        )

    try:
        payload = _extract_dispatch_result_payload(stdout)
        return _validate_payload(request, payload)
    except WtimpDispatchError as exc:
        raise WtimpDispatchError(
            exc.code,
            str(exc),
            _with_session_cleanup(exc.details, process, stdout=stdout, stderr=stderr),
        ) from exc
