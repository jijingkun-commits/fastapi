#!/usr/bin/env python3
"""Codex App monitor script.

Checks FastAPI health endpoints and optionally runs a lightweight Codex probe.
Exits non-zero when checks fail so it can be used by launchd/systemd/cron.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request


@dataclass
class CheckResult:
    name: str
    ok: bool
    status_code: int | None
    latency_ms: int
    detail: str


def _build_headers(bearer_token: str | None = None, *, include_json_content_type: bool = False) -> dict[str, str]:
    headers: dict[str, str] = {}
    if include_json_content_type:
        headers["Content-Type"] = "application/json"
    if bearer_token:
        token = bearer_token.strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


def _http_get_json(url: str, timeout: int, bearer_token: str | None = None) -> tuple[int, dict[str, Any], int]:
    start = time.perf_counter()
    req = request.Request(url=url, method="GET", headers=_build_headers(bearer_token))
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw else {}
        latency_ms = int((time.perf_counter() - start) * 1000)
        return int(resp.status), data, latency_ms


def _http_post_json(
    url: str,
    payload: dict[str, Any],
    timeout: int,
    bearer_token: str | None = None,
) -> tuple[int, dict[str, Any], int]:
    start = time.perf_counter()
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url=url,
        data=body,
        method="POST",
        headers=_build_headers(bearer_token, include_json_content_type=True),
    )
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw) if raw else {}
        latency_ms = int((time.perf_counter() - start) * 1000)
        return int(resp.status), data, latency_ms


def _check_endpoint(
    name: str,
    url: str,
    timeout: int,
    validator,
    bearer_token: str | None = None,
) -> CheckResult:
    try:
        status, payload, latency = _http_get_json(url, timeout, bearer_token=bearer_token)
        ok, detail = validator(status, payload)
        return CheckResult(name=name, ok=ok, status_code=status, latency_ms=latency, detail=detail)
    except error.HTTPError as exc:
        return CheckResult(
            name=name,
            ok=False,
            status_code=int(exc.code),
            latency_ms=0,
            detail=f"http_error: {exc.reason}",
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name=name, ok=False, status_code=None, latency_ms=0, detail=f"exception: {exc}")


def _validate_health(status: int, payload: dict[str, Any]) -> tuple[bool, str]:
    ok = status == 200 and payload.get("status") == "ok"
    return ok, f"status={payload.get('status')}"


def _validate_db(status: int, payload: dict[str, Any]) -> tuple[bool, str]:
    ok = status == 200 and payload.get("status") == "ok" and payload.get("db") is True
    return ok, f"status={payload.get('status')},db={payload.get('db')}"


def _validate_pool(status: int, payload: dict[str, Any]) -> tuple[bool, str]:
    pool = payload.get("pool") if isinstance(payload, dict) else None
    ok = status == 200 and payload.get("status") == "ok" and isinstance(pool, dict)
    if not ok:
        return False, "pool payload invalid"
    required = ["size", "checked_out", "overflow"]
    missing = [key for key in required if key not in pool]
    if missing:
        return False, f"pool missing keys: {missing}"
    return True, f"size={pool.get('size')},checked_out={pool.get('checked_out')},overflow={pool.get('overflow')}"


def _validate_minio(status: int, payload: dict[str, Any]) -> tuple[bool, str]:
    minio = payload.get("minio") if isinstance(payload, dict) else None
    healthy = isinstance(minio, dict) and minio.get("healthy") is True
    ok = status == 200 and healthy
    return ok, f"healthy={healthy}"


def _run_codex_probe(
    base_url: str,
    timeout: int,
    prompt: str,
    bearer_token: str | None = None,
) -> CheckResult:
    url = f"{base_url.rstrip('/')}/dev-tools/codex/exec"
    payload = {
        "prompt": prompt,
        "sandbox": "read-only",
        "timeout_sec": min(max(timeout, 10), 1800),
    }
    try:
        status, body, latency = _http_post_json(url, payload, timeout, bearer_token=bearer_token)
        ok = status == 200 and body.get("ok") is True
        detail = f"ok={body.get('ok')},exit={body.get('exit_code')},duration_ms={body.get('duration_ms')}"
        return CheckResult(name="codex_exec", ok=ok, status_code=status, latency_ms=latency, detail=detail)
    except error.HTTPError as exc:
        return CheckResult(
            name="codex_exec",
            ok=False,
            status_code=int(exc.code),
            latency_ms=0,
            detail=f"http_error: {exc.reason}",
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(name="codex_exec", ok=False, status_code=None, latency_ms=0, detail=f"exception: {exc}")


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"consecutive_failures": 0, "last_status": "unknown", "last_alerted_failure_count": 0}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"consecutive_failures": 0, "last_status": "unknown", "last_alerted_failure_count": 0}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Codex app monitor")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--timeout", type=int, default=8, help="HTTP timeout in seconds")
    parser.add_argument("--check-minio", action="store_true", help="Enable /health/minio check")
    parser.add_argument("--check-codex", action="store_true", help="Enable /dev-tools/codex/exec probe")
    parser.add_argument("--codex-prompt", default="Reply with: monitor_ok")
    parser.add_argument(
        "--bearer-token",
        default=os.getenv("CODEX_APP_BEARER_TOKEN", ""),
        help="Optional Bearer token for protected endpoints",
    )
    parser.add_argument("--state-file", default="tmp/monitor/codex-app-monitor-state.json")
    parser.add_argument("--alert-threshold", type=int, default=2, help="Consecutive failures before alert")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = args.base_url.rstrip("/")

    token = args.bearer_token.strip() or None

    checks: list[CheckResult] = [
        _check_endpoint("health", f"{base}/health", args.timeout, _validate_health, bearer_token=token),
        _check_endpoint("health_db", f"{base}/health/db", args.timeout, _validate_db, bearer_token=token),
        _check_endpoint("health_pool", f"{base}/health/pool", args.timeout, _validate_pool, bearer_token=token),
    ]

    if args.check_minio:
        checks.append(
            _check_endpoint("health_minio", f"{base}/health/minio", args.timeout, _validate_minio, bearer_token=token)
        )

    if args.check_codex:
        checks.append(_run_codex_probe(base, timeout=max(args.timeout, 20), prompt=args.codex_prompt, bearer_token=token))

    all_ok = all(item.ok for item in checks)

    state_file = Path(args.state_file)
    state = _read_state(state_file)

    if all_ok:
        state["consecutive_failures"] = 0
        state["last_status"] = "ok"
    else:
        state["consecutive_failures"] = int(state.get("consecutive_failures", 0)) + 1
        state["last_status"] = "failed"

    should_alert = state["consecutive_failures"] >= args.alert_threshold and (
        int(state.get("last_alerted_failure_count", 0)) < state["consecutive_failures"]
    )

    if should_alert:
        state["last_alerted_failure_count"] = state["consecutive_failures"]

    if all_ok and int(state.get("last_alerted_failure_count", 0)) > 0:
        state["last_alerted_failure_count"] = 0

    _write_state(state_file, state)

    payload = {
        "ok": all_ok,
        "base_url": base,
        "checked_at": int(time.time()),
        "checks": [
            {
                "name": c.name,
                "ok": c.ok,
                "status_code": c.status_code,
                "latency_ms": c.latency_ms,
                "detail": c.detail,
            }
            for c in checks
        ],
        "consecutive_failures": state["consecutive_failures"],
        "should_alert": bool(should_alert),
        "alert_threshold": args.alert_threshold,
        "state_file": str(state_file),
    }

    print(json.dumps(payload, ensure_ascii=False))
    return 0 if all_ok else 2


if __name__ == "__main__":
    sys.exit(main())
