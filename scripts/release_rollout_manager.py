#!/usr/bin/env python3
"""C-5 发布与回滚管理脚本（规则体系/命令注册中心）。

能力：
1. 查看当前灰度状态（env + db）。
2. 按目标设置灰度比例与开关（rollout）。
3. 一键回滚目标能力（rollback）。

示例：
    python3 scripts/release_rollout_manager.py status
    python3 scripts/release_rollout_manager.py rollout --target ruleset_v2 --percent 10
    python3 scripts/release_rollout_manager.py rollout --target all --percent 30 --sync
    python3 scripts/release_rollout_manager.py rollback --target prompt_registry_v2 --reason "prompt drift" --sync
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text

from app.db.session import engine

engine.echo = False


@dataclass(frozen=True)
class ReleaseTarget:
    """灰度目标定义。"""

    name: str
    title: str
    env_enable_key: str
    env_rollout_key: str
    db_enable_key: str
    db_rollout_key: str


TARGETS: Dict[str, ReleaseTarget] = {
    "ruleset_v2": ReleaseTarget(
        name="ruleset_v2",
        title="规则体系 V2",
        env_enable_key="ENABLE_RULESET_V2",
        env_rollout_key="RULESET_V2_ROLLOUT_PERCENTAGE",
        db_enable_key="feature.enable_ruleset_v2",
        db_rollout_key="release.ruleset_v2_rollout_percentage",
    ),
    "prompt_registry_v2": ReleaseTarget(
        name="prompt_registry_v2",
        title="命令注册中心 V2",
        env_enable_key="ENABLE_PROMPT_REGISTRY_V2",
        env_rollout_key="PROMPT_REGISTRY_V2_ROLLOUT_PERCENTAGE",
        db_enable_key="feature.enable_prompt_registry_v2",
        db_rollout_key="release.prompt_registry_v2_rollout_percentage",
    ),
}


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="C-5 灰度与回滚管理")
    parser.add_argument(
        "--env-file",
        default=".env.dev",
        help="环境变量文件路径（默认: .env.dev）",
    )
    parser.add_argument(
        "--channel",
        choices=["env", "db", "both"],
        default="both",
        help="写入通道（默认: both）",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="执行后触发命令镜像同步（scripts/sync_rules_to_cc.py）",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="查看灰度状态")

    rollout_parser = subparsers.add_parser("rollout", help="设置灰度比例")
    rollout_parser.add_argument(
        "--target",
        choices=["ruleset_v2", "prompt_registry_v2", "all"],
        required=True,
        help="灰度目标",
    )
    rollout_parser.add_argument(
        "--percent",
        type=int,
        required=True,
        help="灰度比例（0-100）",
    )
    rollout_parser.add_argument(
        "--disable",
        action="store_true",
        help="强制关闭（忽略 percent，并将比例置 0）",
    )

    rollback_parser = subparsers.add_parser("rollback", help="回滚目标能力")
    rollback_parser.add_argument(
        "--target",
        choices=["ruleset_v2", "prompt_registry_v2", "all"],
        required=True,
        help="回滚目标",
    )
    rollback_parser.add_argument(
        "--reason",
        default="manual rollback",
        help="回滚原因（用于写入 env 审计字段）",
    )

    return parser.parse_args()


def _normalize_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _read_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    values: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _write_env_file(path: Path, updates: Dict[str, str]) -> None:
    existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(updates)
    out_lines: list[str] = []

    for raw_line in existing_lines:
        line = raw_line
        matched = False
        for key, value in list(remaining.items()):
            if re.match(rf"^\s*{re.escape(key)}\s*=", line):
                out_lines.append(f"{key}={value}")
                remaining.pop(key, None)
                matched = True
                break
        if not matched:
            out_lines.append(raw_line)

    if remaining:
        if out_lines and out_lines[-1].strip():
            out_lines.append("")
        for key, value in remaining.items():
            out_lines.append(f"{key}={value}")

    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def _set_db_values(updates: Dict[str, tuple[str, str, str, str]]) -> None:
    """写入数据库配置。

    updates: key -> (value, value_type, category, description)
    """

    sql = text(
        """
        INSERT INTO t_system_config (
            config_key, config_value, value_type, category, description,
            is_secret, is_readonly, create_time, update_time
        )
        VALUES (
            :config_key, :config_value, :value_type, :category, :description,
            false, false, NOW(), NOW()
        )
        ON CONFLICT (config_key)
        DO UPDATE SET
            config_value = EXCLUDED.config_value,
            value_type = EXCLUDED.value_type,
            category = EXCLUDED.category,
            description = EXCLUDED.description,
            update_time = NOW()
        """
    )

    with engine.begin() as conn:
        for key, (value, value_type, category, description) in updates.items():
            conn.execute(
                sql,
                {
                    "config_key": key,
                    "config_value": value,
                    "value_type": value_type,
                    "category": category,
                    "description": description,
                },
            )


def _get_target_list(target_name: str) -> list[ReleaseTarget]:
    if target_name == "all":
        return [TARGETS["ruleset_v2"], TARGETS["prompt_registry_v2"]]
    return [TARGETS[target_name]]


def _print_status(env_file: Path, include_db: bool) -> int:
    env_values = _read_env_file(env_file)
    db_values: Dict[str, str] = {}

    db_error = None
    if include_db:
        try:
            keys: list[str] = []
            for target in TARGETS.values():
                keys.append(target.db_enable_key)
                keys.append(target.db_rollout_key)
            sql = text(
                "SELECT config_key, config_value FROM t_system_config WHERE config_key = ANY(:keys)"
            )
            with engine.begin() as conn:
                rows = conn.execute(sql, {"keys": keys}).all()
            db_values = {row[0]: row[1] for row in rows}
        except Exception as exc:  # pragma: no cover - 依赖运行时数据库
            db_error = str(exc)

    print("=" * 72)
    print("C-5 灰度状态")
    print("=" * 72)
    print(f"- env_file: {env_file}")
    print(f"- generated_at: {datetime.now(timezone.utc).isoformat()}")

    for target in TARGETS.values():
        env_enable = env_values.get(target.env_enable_key, "-")
        env_rollout = env_values.get(target.env_rollout_key, "-")
        print(f"\n[{target.title}]")
        print(f"  env  {target.env_enable_key}={env_enable}")
        print(f"  env  {target.env_rollout_key}={env_rollout}")
        if include_db:
            print(f"  db   {target.db_enable_key}={db_values.get(target.db_enable_key, '-')}")
            print(f"  db   {target.db_rollout_key}={db_values.get(target.db_rollout_key, '-')}")

    if db_error:
        print(f"\n[警告] 读取数据库失败：{db_error}")
        return 1
    return 0


def _rollout(
    *,
    env_file: Path,
    targets: list[ReleaseTarget],
    percent: int,
    disable: bool,
    channel: str,
) -> int:
    if percent < 0 or percent > 100:
        print("percent 必须在 0-100 之间", file=sys.stderr)
        return 2

    enable = (percent > 0) and not disable
    final_percent = 0 if disable else percent

    env_updates: Dict[str, str] = {}
    db_updates: Dict[str, tuple[str, str, str, str]] = {}

    for target in targets:
        env_updates[target.env_enable_key] = "true" if enable else "false"
        env_updates[target.env_rollout_key] = str(final_percent)

        db_updates[target.db_enable_key] = (
            "true" if enable else "false",
            "boolean",
            "feature",
            f"{target.title} 开关（C-5 灰度发布）",
        )
        db_updates[target.db_rollout_key] = (
            str(final_percent),
            "number",
            "release",
            f"{target.title} 灰度比例（C-5）",
        )

    if channel in {"env", "both"}:
        _write_env_file(env_file, env_updates)
    if channel in {"db", "both"}:
        try:
            _set_db_values(db_updates)
        except Exception as exc:  # pragma: no cover - 依赖运行时数据库
            print(f"写入 DB 失败：{exc}", file=sys.stderr)
            return 2

    print(
        f"rollout 已更新: targets={[t.name for t in targets]} enable={enable} "
        f"percent={final_percent} channel={channel}"
    )
    return 0


def _rollback(
    *,
    env_file: Path,
    targets: list[ReleaseTarget],
    reason: str,
    channel: str,
) -> int:
    rollback_time = datetime.now(timezone.utc).isoformat()
    env_updates: Dict[str, str] = {
        "RELEASE_V2_LAST_ROLLBACK_AT": rollback_time,
        "RELEASE_V2_LAST_ROLLBACK_REASON": reason,
    }
    db_updates: Dict[str, tuple[str, str, str, str]] = {}

    for target in targets:
        env_updates[target.env_enable_key] = "false"
        env_updates[target.env_rollout_key] = "0"

        db_updates[target.db_enable_key] = (
            "false",
            "boolean",
            "feature",
            f"{target.title} 开关（C-5 回滚）",
        )
        db_updates[target.db_rollout_key] = (
            "0",
            "number",
            "release",
            f"{target.title} 灰度比例（C-5 回滚）",
        )

    if channel in {"env", "both"}:
        _write_env_file(env_file, env_updates)
    if channel in {"db", "both"}:
        try:
            _set_db_values(db_updates)
        except Exception as exc:  # pragma: no cover - 依赖运行时数据库
            print(f"写入 DB 失败：{exc}", file=sys.stderr)
            return 2

    print(
        f"rollback 已执行: targets={[t.name for t in targets]} "
        f"reason={reason} at={rollback_time} channel={channel}"
    )
    return 0


def _run_sync(targets: list[ReleaseTarget]) -> int:
    target_names = {target.name for target in targets}
    cmd = [sys.executable, "scripts/sync_rules_to_cc.py"]
    if target_names == {"ruleset_v2"}:
        cmd.extend(["--only", "rules"])
    elif target_names == {"prompt_registry_v2"}:
        cmd.extend(["--only", "commands"])

    completed = subprocess.run(cmd, cwd=PROJECT_ROOT, check=False)
    return int(completed.returncode)


def main() -> int:
    args = parse_args()
    env_file = (PROJECT_ROOT / args.env_file).resolve()

    if args.command == "status":
        return _print_status(env_file=env_file, include_db=args.channel in {"db", "both"})

    if args.command == "rollout":
        targets = _get_target_list(args.target)
        code = _rollout(
            env_file=env_file,
            targets=targets,
            percent=args.percent,
            disable=args.disable,
            channel=args.channel,
        )
        if code != 0:
            return code
        if args.sync:
            return _run_sync(targets)
        return 0

    if args.command == "rollback":
        targets = _get_target_list(args.target)
        code = _rollback(
            env_file=env_file,
            targets=targets,
            reason=args.reason,
            channel=args.channel,
        )
        if code != 0:
            return code
        if args.sync:
            return _run_sync(targets)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
