#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
GLOBAL_CONFIG="${CODEX_HOME:-$HOME/.codex}/config.toml"
PROJECT_CONFIG="$ROOT_DIR/.mcp.json"

python3 - "$ROOT_DIR" "$GLOBAL_CONFIG" "$PROJECT_CONFIG" <<'PY'
import json
import os
import selectors
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

root_dir = Path(sys.argv[1])
global_config = Path(sys.argv[2])
project_config = Path(sys.argv[3])

status_order = {"OK": 0, "BLOCKED": 1, "FAIL": 2}
rows = []
HANDSHAKE_TIMEOUT_SECONDS = 10


def add_row(name: str, enabled: bool, status: str, detail: str) -> None:
    rows.append((name, "enabled" if enabled else "disabled", status, detail))


def command_exists(command: str) -> bool:
    if not command:
        return False
    if os.path.isabs(command):
        return os.path.exists(command)
    return shutil.which(command) is not None


def handshake_json_line(command: str, args: list[str], env: dict[str, str]) -> tuple[bool, str]:
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "check_mcp_health", "version": "1.0"},
        },
    }
    wire = json.dumps(req).encode("utf-8") + b"\n"
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    proc = None
    selector = selectors.DefaultSelector()

    def decode(chunks: list[bytes]) -> str:
        return b"".join(chunks).decode("utf-8", errors="replace").strip()

    try:
        proc = subprocess.Popen(
            [command, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        assert proc.stdin and proc.stdout and proc.stderr
        proc.stdin.write(wire)
        proc.stdin.flush()

        selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
        selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
        deadline = time.monotonic() + HANDSHAKE_TIMEOUT_SECONDS

        while time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            events = selector.select(timeout=min(0.2, remaining))
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 4096)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stdout":
                    stdout_chunks.append(chunk)
                else:
                    stderr_chunks.append(chunk)

            stdout_text = decode(stdout_chunks)
            if '"jsonrpc"' in stdout_text and '"result"' in stdout_text:
                return True, "initialize handshake ok"

            if proc.poll() is not None and not selector.get_map():
                break
    except FileNotFoundError as exc:
        return False, f"launch failed: {exc}"
    finally:
        try:
            selector.close()
        except Exception:
            pass
        if proc is not None:
            try:
                if proc.stdin:
                    proc.stdin.close()
            except Exception:
                pass
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=1)

    stdout_text = decode(stdout_chunks)
    stderr_text = decode(stderr_chunks)
    detail = stdout_text or stderr_text or (f"exit={proc.returncode}" if proc is not None else "handshake timeout")
    return False, detail[:200]


def read_toml(path: Path):
    with path.open("rb") as handle:
        return tomllib.load(handle)


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


print("MCP Health Check")
print(f"root={root_dir}")
print(f"global_config={global_config}")
print(f"project_config={project_config}")
print(f"pwd={Path.cwd()}")
print(f"branch={subprocess.run(['git', 'branch', '--show-current'], cwd=root_dir, capture_output=True, text=True, check=False).stdout.strip()}")
print("---")

if not global_config.exists():
    print(f"FAIL global config missing: {global_config}")
    sys.exit(1)
if not project_config.exists():
    print(f"FAIL project config missing: {project_config}")
    sys.exit(1)

codex = read_toml(global_config)
project = read_json(project_config)
servers = codex.get("mcp_servers", {})
project_servers = project.get("mcpServers", {})

for name, config in sorted(servers.items()):
    enabled = config.get("enabled", True)
    command = config.get("command", "")
    detail = ""
    status = "OK"

    if not enabled:
        add_row(name, enabled, "OK", "configured as disabled")
        continue

    if not command_exists(command):
        add_row(name, enabled, "FAIL", f"command missing: {command}")
        continue

    if name == "github-mcp-server":
        token = config.get("env", {}).get("GITHUB_PERSONAL_ACCESS_TOKEN") or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
        if not token:
            status = "FAIL"
            detail = "missing GITHUB_PERSONAL_ACCESS_TOKEN in user-local runtime"
        elif project_servers.get(name, {}).get("env", {}).get("GITHUB_PERSONAL_ACCESS_TOKEN"):
            status = "FAIL"
            detail = "project mirror still contains a GitHub token"
        else:
            ok, handshake_detail = handshake_json_line(command, config.get("args", []), {**os.environ, **config.get("env", {})})
            status = "OK" if ok else "FAIL"
            detail = f"docker command present; {handshake_detail}"
    elif name == "vibe_kanban":
        if not os.access(command, os.X_OK):
            status = "FAIL"
            detail = f"binary not executable: {command}"
        else:
            runtime_env = {**os.environ, **config.get("env", {})}
            backend_port = runtime_env.get("BACKEND_PORT")
            port_file = Path(tempfile.gettempdir()) / "vibe-kanban" / "vibe-kanban.port"
            if not backend_port and not port_file.exists():
                status = "BLOCKED"
                detail = f"missing BACKEND_PORT and port file: {port_file}"
            else:
                ok, handshake_detail = handshake_json_line(command, config.get("args", []), runtime_env)
                status = "OK" if ok else "FAIL"
                detail = f"local binary present; {handshake_detail}"
    elif name in {"postgres", "postgres-data-db", "minio", "context7", "playwright"}:
        ok, handshake_detail = handshake_json_line(command, config.get("args", []), {**os.environ, **config.get("env", {})})
        status = "OK" if ok else "FAIL"
        detail = handshake_detail
    else:
        detail = f"command present: {command}"

    project_mirror = project_servers.get(name)
    if project_mirror is None and name not in {"mysql", "sqlite"}:
        status = "BLOCKED" if status == "OK" else status
        detail = f"{detail}; project mirror missing"

    add_row(name, enabled, status, detail)

name_width = max(len(row[0]) for row in rows)
mode_width = max(len(row[1]) for row in rows)
status_width = max(len(row[2]) for row in rows)
print(f"{'server'.ljust(name_width)}  {'mode'.ljust(mode_width)}  {'status'.ljust(status_width)}  detail")
print(f"{'-' * name_width}  {'-' * mode_width}  {'-' * status_width}  {'-' * 48}")
for row in sorted(rows, key=lambda item: (status_order[item[2]], item[0])):
    print(f"{row[0].ljust(name_width)}  {row[1].ljust(mode_width)}  {row[2].ljust(status_width)}  {row[3]}")

fail_count = sum(1 for row in rows if row[2] == "FAIL")
blocked_count = sum(1 for row in rows if row[2] == "BLOCKED")
disabled_count = sum(1 for row in rows if row[1] == "disabled")
enabled_ok_count = sum(1 for row in rows if row[1] == "enabled" and row[2] == "OK")
print("---")
print(f"summary: enabled_ok={enabled_ok_count} disabled={disabled_count} blocked={blocked_count} fail={fail_count}")
PY
