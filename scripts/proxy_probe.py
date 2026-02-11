#!/usr/bin/env python3
"""中转供应商可用性探针。

用途：
- 对比 OpenAI SDK 与 curl 两种调用路径
- 同时检测 /v1 与非 /v1 base URL
- 输出可直接提交供应商工单的最小证据

示例：
  venv/bin/python scripts/proxy_probe.py \
    --base https://gmn.chuangzuoli.com \
    --api-key sk-xxxx \
    --model gpt-5.2
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class ProbeResult:
    channel: str
    method: str
    url: str
    status: str
    detail: str


def _normalize_base(base: str) -> str:
    return base.rstrip("/")


def _build_variants(base: str) -> list[str]:
    base = _normalize_base(base)
    if base.endswith("/v1"):
        return [base, base[:-3]]
    return [f"{base}/v1", base]


def _safe_text(text: str, limit: int = 240) -> str:
    if text is None:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    return text[:limit]


def probe_sdk(base_url: str, api_key: str, model: str) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    client = OpenAI(base_url=base_url, api_key=api_key)

    # models list
    try:
        client.models.list()
        results.append(ProbeResult("sdk", "GET", f"{base_url}/models", "PASS", "models.list ok"))
    except Exception as exc:  # noqa: BLE001
        resp = getattr(exc, "response", None)
        status_code = getattr(resp, "status_code", "-") if resp else "-"
        body = _safe_text(getattr(resp, "text", "")) if resp else ""
        results.append(
            ProbeResult(
                "sdk",
                "GET",
                f"{base_url}/models",
                "FAIL",
                f"{type(exc).__name__} status={status_code} body={body or str(exc)}",
            )
        )

    # responses create
    try:
        response = client.responses.create(model=model, input="hi", store=False)
        output_text = _safe_text(getattr(response, "output_text", "") or "")
        results.append(ProbeResult("sdk", "POST", f"{base_url}/responses", "PASS", f"output={output_text}"))
    except Exception as exc:  # noqa: BLE001
        resp = getattr(exc, "response", None)
        status_code = getattr(resp, "status_code", "-") if resp else "-"
        body = _safe_text(getattr(resp, "text", "")) if resp else ""
        results.append(
            ProbeResult(
                "sdk",
                "POST",
                f"{base_url}/responses",
                "FAIL",
                f"{type(exc).__name__} status={status_code} body={body or str(exc)}",
            )
        )

    return results


def probe_curl(base_url: str, api_key: str, model: str) -> list[ProbeResult]:
    results: list[ProbeResult] = []

    tests = [
        ("GET", f"{base_url}/models", None),
        ("POST", f"{base_url}/responses", json.dumps({"model": model, "input": "hi", "store": False})),
    ]

    for method, url, payload in tests:
        cmd = [
            "curl",
            "--http1.1",
            "-sS",
            "-i",
            "-X",
            method,
            url,
            "-H",
            f"Authorization: Bearer {api_key}",
            "-H",
            "Content-Type: application/json",
        ]
        if payload is not None:
            cmd.extend(["-d", payload])

        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=25)
            first_line = output.splitlines()[0] if output.splitlines() else ""
            sample = _safe_text(" ".join(output.splitlines()[:8]), limit=320)
            status = "PASS" if " 200 " in first_line else "FAIL"
            results.append(
                ProbeResult(
                    "curl",
                    method,
                    url,
                    status,
                    f"{first_line} sample={sample}",
                )
            )
        except subprocess.CalledProcessError as exc:
            text = _safe_text(exc.output or "", limit=320)
            results.append(ProbeResult("curl", method, url, "FAIL", f"exit={exc.returncode} output={text}"))
        except Exception as exc:  # noqa: BLE001
            results.append(ProbeResult("curl", method, url, "FAIL", f"{type(exc).__name__}: {exc}"))

    return results


def print_results(results: list[ProbeResult]) -> None:
    print("\n=== Probe Results ===")
    for result in results:
        print(f"[{result.status}] {result.channel} {result.method} {result.url}")
        print(f"       {result.detail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="中转供应商 API 探针")
    parser.add_argument("--base", required=True, help="中转网关基础地址，如 https://gmn.chuangzuoli.com")
    parser.add_argument("--api-key", required=True, help="中转 API Key")
    parser.add_argument("--model", default="gpt-5.2", help="测试模型，默认 gpt-5.2")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bases = _build_variants(args.base)

    all_results: list[ProbeResult] = []
    for base in bases:
        all_results.extend(probe_sdk(base, args.api_key, args.model))
        all_results.extend(probe_curl(base, args.api_key, args.model))

    print_results(all_results)

    fail_count = sum(1 for item in all_results if item.status == "FAIL")
    print(f"\nsummary: total={len(all_results)} fail={fail_count} pass={len(all_results)-fail_count}")
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
