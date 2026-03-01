#!/usr/bin/env python3
"""Run Codex turn-by-turn with persisted logs and compact summaries."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Codex turn supervisor")
    parser.add_argument("--prompt", required=True, help="User instruction for this turn")
    parser.add_argument("--workdir", default=".", help="Working directory for codex")
    parser.add_argument("--session-id", default="", help="Existing session id; empty creates a new one")
    parser.add_argument("--model", default="", help="Optional model id")
    parser.add_argument("--sandbox", default="read-only", choices=["read-only", "workspace-write", "danger-full-access"])
    parser.add_argument("--timeout", type=int, default=900, help="Timeout in seconds")
    parser.add_argument("--state-dir", default="tmp/codex-supervisor", help="State and log root dir")
    parser.add_argument("--history-turns", type=int, default=3, help="Turns to keep in synthesized context")
    parser.add_argument("--answer-preview-chars", type=int, default=800)
    return parser.parse_args()


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_context_prompt(user_prompt: str, history: list[dict[str, Any]], history_turns: int) -> str:
    if not history:
        return user_prompt

    selected = history[-history_turns:]
    lines = [
        "Context from previous turns:",
    ]
    for turn in selected:
        lines.append(f"- Turn {turn.get('turn_index')}")
        lines.append(f"  user: {turn.get('user_prompt', '').strip()}")
        assistant = (turn.get("assistant_answer") or "").strip()
        if assistant:
            lines.append(f"  assistant: {assistant[:1200]}")

    lines.append("Current user instruction:")
    lines.append(user_prompt)
    return "\n".join(lines)


def _extract_assistant_answer(stdout_text: str) -> str:
    lines = stdout_text.splitlines()
    chunks: list[str] = []
    capture = False

    for line in lines:
        stripped = line.rstrip()
        if stripped == "codex":
            capture = True
            continue
        if capture:
            lower = stripped.lower()
            if lower.startswith("tokens used"):
                break
            if stripped.startswith("202") and " WARN " in stripped:
                break
            chunks.append(stripped)

    answer = "\n".join(chunks).strip()
    if answer:
        return answer

    non_empty = [ln.strip() for ln in lines if ln.strip()]
    if non_empty:
        return non_empty[-1]
    return ""


def main() -> int:
    args = _parse_args()

    state_root = Path(args.state_dir).resolve()
    session_id = args.session_id.strip() or time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    session_dir = state_root / session_id
    session_file = session_dir / "session.json"

    session_state = _load_json(
        session_file,
        {
            "session_id": session_id,
            "workdir": str(Path(args.workdir).resolve()),
            "created_at": int(time.time()),
            "turns": [],
        },
    )

    turns = session_state.get("turns", [])
    turn_index = len(turns) + 1
    turn_id = f"t{turn_index:03d}"

    final_prompt = _build_context_prompt(args.prompt, turns, args.history_turns)

    command: list[str] = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        args.sandbox,
        final_prompt,
    ]
    if args.model.strip():
        command = ["codex", "-m", args.model.strip(), "exec", "--skip-git-repo-check", "--sandbox", args.sandbox, final_prompt]

    started = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            cwd=args.workdir,
            capture_output=True,
            text=True,
            timeout=args.timeout,
            check=False,
        )
        timed_out = False
        exit_code = proc.returncode
        stdout_text = proc.stdout or ""
        stderr_text = proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = 124
        stdout_text = exc.stdout or ""
        stderr_text = (exc.stderr or "") + f"\nTimeout after {args.timeout}s"

    duration_ms = int((time.perf_counter() - started) * 1000)

    session_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = session_dir / f"{turn_id}.stdout.log"
    stderr_path = session_dir / f"{turn_id}.stderr.log"
    stdout_path.write_text(stdout_text, encoding="utf-8")
    stderr_path.write_text(stderr_text, encoding="utf-8")

    assistant_answer = _extract_assistant_answer(stdout_text)
    assistant_preview = assistant_answer[: args.answer_preview_chars]

    turn_record = {
        "turn_index": turn_index,
        "turn_id": turn_id,
        "user_prompt": args.prompt,
        "prompt_sent_chars": len(final_prompt),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        "assistant_answer": assistant_answer,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "ts": int(time.time()),
    }

    turns.append(turn_record)
    session_state["turns"] = turns
    session_state["updated_at"] = int(time.time())
    _dump_json(session_file, session_state)

    result = {
        "ok": exit_code == 0,
        "session_id": session_id,
        "turn_id": turn_id,
        "turn_index": turn_index,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "assistant_preview": assistant_preview,
        "assistant_answer_chars": len(assistant_answer),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "session_file": str(session_file),
    }

    print(json.dumps(result, ensure_ascii=False))
    return 0 if exit_code == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
