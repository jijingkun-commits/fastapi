"""配置健康检查脚本（中文注释）。

目标：
1. 基于配置契约检查 DB 动态配置覆盖率。
2. 输出 DB 与环境变量在运行时优先级上的差异。
3. 发现 askdata/data_access 等历史键冲突或主键缺失问题。

运行方式：
    python scripts/config_doctor.py
    python scripts/config_doctor.py --show-all
    python scripts/config_doctor.py --strict
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config_contract import CONFIG_SPECS, ConfigSpec
from app.db.session import SessionLocal, engine
from app.models.system_config import SystemConfig

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
engine.echo = False


@dataclass(frozen=True)
class CheckRow:
    """单个配置项的检查结果。"""

    key: str
    source: str
    status: str
    effective_from: str
    db_detail: str
    env_detail: str


@dataclass(frozen=True)
class Issue:
    """问题项。"""

    severity: str
    code: str
    key: str
    message: str


SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="配置健康检查（契约/DB/ENV 差异）")
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="显示所有配置项（默认仅显示异常项）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="当存在 P0/P1 问题时返回非零退出码",
    )
    return parser.parse_args()


def _is_non_empty(value: str | None) -> bool:
    """判断字符串是否为有效值。"""

    return value is not None and value.strip() != ""


def _normalize_value(value: str | None, value_type: str) -> str:
    """标准化值用于比较，避免格式差异导致误判。"""

    if not _is_non_empty(value):
        return ""

    text = value.strip()

    if value_type == "number":
        try:
            number = float(text)
            return str(int(number)) if number.is_integer() else str(number)
        except ValueError:
            return text.lower()

    if value_type == "boolean":
        normalized = text.lower()
        truthy = {"1", "true", "yes", "on", "enabled"}
        falsy = {"0", "false", "no", "off", "disabled"}
        if normalized in truthy:
            return "true"
        if normalized in falsy:
            return "false"
        return normalized

    if value_type == "json":
        try:
            loaded = json.loads(text)
            return json.dumps(loaded, sort_keys=True, ensure_ascii=True)
        except json.JSONDecodeError:
            return text.lower()

    if "," in text:
        parts = [part.strip().lower() for part in text.split(",") if part.strip()]
        deduped = sorted(set(parts))
        return ",".join(deduped)

    return text.lower()


def _load_db_map() -> dict[str, SystemConfig]:
    """加载主库中的系统配置。"""

    with SessionLocal() as db:
        rows = db.execute(select(SystemConfig)).scalars().all()
    return {row.config_key: row for row in rows}


def _validate_contract(specs: dict[str, ConfigSpec]) -> list[Issue]:
    """检查契约定义本身是否存在冲突。"""

    issues: list[Issue] = []
    db_key_owner: dict[str, str] = {}

    for logical_key, spec in specs.items():
        if spec.source == "env-only" and not spec.env_key:
            issues.append(
                Issue(
                    severity="P1",
                    code="ENV_KEY_MISSING",
                    key=logical_key,
                    message="env-only 配置缺少 env_key 定义",
                )
            )

        for db_key in spec.all_db_keys():
            if not db_key:
                issues.append(
                    Issue(
                        severity="P1",
                        code="DB_KEY_EMPTY",
                        key=logical_key,
                        message="配置契约包含空 db_key",
                    )
                )
                continue

            owner = db_key_owner.get(db_key)
            if owner and owner != logical_key:
                issues.append(
                    Issue(
                        severity="P0",
                        code="DB_KEY_DUPLICATED",
                        key=logical_key,
                        message=f"db_key={db_key} 同时被 {owner} 与 {logical_key} 使用",
                    )
                )
            else:
                db_key_owner[db_key] = logical_key

    return issues


def _format_env_detail(spec: ConfigSpec) -> tuple[str, str | None]:
    """生成环境变量展示描述。"""

    if not spec.env_key:
        return "-", None

    env_value = os.getenv(spec.env_key)
    if _is_non_empty(env_value):
        return f"{spec.env_key}=set", env_value
    return f"{spec.env_key}=unset", None


def _analyze_dynamic_spec(spec: ConfigSpec, db_map: dict[str, SystemConfig]) -> tuple[CheckRow, list[Issue]]:
    """分析 db-dynamic 配置项。"""

    issues: list[Issue] = []
    primary_key = spec.db_key or spec.key
    primary_row = db_map.get(primary_key)
    primary_value = primary_row.config_value if primary_row else None

    alias_rows: list[tuple[str, str]] = []
    for alias in spec.aliases:
        alias_row = db_map.get(alias)
        if alias_row and _is_non_empty(alias_row.config_value):
            alias_rows.append((alias, alias_row.config_value))

    env_detail, env_value = _format_env_detail(spec)

    if _is_non_empty(primary_value):
        status = "OK"
        effective_from = f"db:{primary_key}"
        db_detail = f"{primary_key}=set"
    elif alias_rows:
        alias_key, _ = alias_rows[0]
        status = "ALIAS_FALLBACK"
        effective_from = f"db:{alias_key}"
        db_detail = f"{primary_key}=unset, alias={alias_key}"
        issues.append(
            Issue(
                severity="P2",
                code="PRIMARY_DB_KEY_MISSING",
                key=spec.key,
                message=f"主键 {primary_key} 缺失，当前回退历史键 {alias_key}",
            )
        )
    elif _is_non_empty(env_value):
        status = "ENV_FALLBACK"
        effective_from = f"env:{spec.env_key}"
        db_detail = f"{primary_key}=unset"
        issues.append(
            Issue(
                severity="P2",
                code="DB_KEY_MISSING_WITH_ENV_FALLBACK",
                key=spec.key,
                message=f"主键 {primary_key} 缺失，当前依赖环境变量 {spec.env_key}",
            )
        )
    else:
        status = "DEFAULT_FALLBACK"
        effective_from = "default"
        db_detail = f"{primary_key}=unset"
        issues.append(
            Issue(
                severity="P2",
                code="DB_AND_ENV_MISSING",
                key=spec.key,
                message=f"主键 {primary_key} 与环境变量 {spec.env_key or '-'} 均缺失，运行时回退默认值",
            )
        )

    if _is_non_empty(primary_value):
        normalized_primary = _normalize_value(primary_value, spec.value_type)
        for alias_key, alias_value in alias_rows:
            normalized_alias = _normalize_value(alias_value, spec.value_type)
            if normalized_alias != normalized_primary:
                issues.append(
                    Issue(
                        severity="P1",
                        code="PRIMARY_LEGACY_CONFLICT",
                        key=spec.key,
                        message=(
                            f"主键 {primary_key} 与历史键 {alias_key} 值冲突，"
                            "已按主键优先生效"
                        ),
                    )
                )

    row = CheckRow(
        key=spec.key,
        source=spec.source,
        status=status,
        effective_from=effective_from,
        db_detail=db_detail,
        env_detail=env_detail,
    )
    return row, issues


def _analyze_env_only_spec(spec: ConfigSpec) -> tuple[CheckRow, list[Issue]]:
    """分析 env-only 配置项。"""

    issues: list[Issue] = []
    env_detail, env_value = _format_env_detail(spec)

    if _is_non_empty(env_value):
        status = "OK"
        effective_from = f"env:{spec.env_key}"
    else:
        status = "MISSING_ENV"
        effective_from = "default"
        issues.append(
            Issue(
                severity="P1",
                code="ENV_ONLY_MISSING",
                key=spec.key,
                message=f"env-only 配置缺失环境变量 {spec.env_key}",
            )
        )

    row = CheckRow(
        key=spec.key,
        source=spec.source,
        status=status,
        effective_from=effective_from,
        db_detail="-",
        env_detail=env_detail,
    )
    return row, issues


def _collect_known_db_keys(specs: dict[str, ConfigSpec]) -> set[str]:
    """收集契约中已声明的数据库配置键。"""

    keys: set[str] = set()
    for spec in specs.values():
        keys.update(spec.all_db_keys())
    return keys


def _sort_issues(issues: Iterable[Issue]) -> list[Issue]:
    """按严重级别与键名排序。"""

    return sorted(
        issues,
        key=lambda item: (
            SEVERITY_ORDER.get(item.severity, 99),
            item.code,
            item.key,
        ),
    )


def _print_rows(rows: list[CheckRow], show_all: bool) -> None:
    """输出配置项检查结果。"""

    print("\n[配置项检查]")
    for row in rows:
        if not show_all and row.status == "OK":
            continue
        print(
            f"- {row.key} | status={row.status} | effective={row.effective_from} "
            f"| db={row.db_detail} | env={row.env_detail}"
        )


def _print_issues(issues: list[Issue]) -> None:
    """输出问题清单。"""

    print("\n[问题清单]")
    if not issues:
        print("- 无")
        return

    for issue in issues:
        print(
            f"- {issue.severity} {issue.code} | key={issue.key} | {issue.message}"
        )


def _print_summary(rows: list[CheckRow], issues: list[Issue], unknown_db_keys: list[str]) -> None:
    """输出统计摘要。"""

    total = len(rows)
    dynamic_total = sum(1 for row in rows if row.source == "db-dynamic")
    env_only_total = sum(1 for row in rows if row.source == "env-only")
    status_counter: dict[str, int] = {}
    for row in rows:
        status_counter[row.status] = status_counter.get(row.status, 0) + 1

    severity_counter = {"P0": 0, "P1": 0, "P2": 0}
    for issue in issues:
        if issue.severity in severity_counter:
            severity_counter[issue.severity] += 1

    print("=" * 72)
    print("配置健康检查（chat_db + 环境变量）")
    print("=" * 72)
    print(f"- 契约配置总数: {total} (db-dynamic={dynamic_total}, env-only={env_only_total})")
    print(
        "- 状态统计: "
        + ", ".join(f"{name}={count}" for name, count in sorted(status_counter.items()))
    )
    print(
        f"- 问题统计: P0={severity_counter['P0']}, "
        f"P1={severity_counter['P1']}, P2={severity_counter['P2']}"
    )
    print(f"- 未纳入契约的 DB 配置键: {len(unknown_db_keys)}")



def main() -> int:
    """脚本入口。"""

    args = parse_args()

    try:
        db_map = _load_db_map()
    except Exception as exc:  # pragma: no cover - 依赖运行环境
        print(f"P0: 无法读取主库配置（DATABASE_URL）: {exc}")
        return 2

    issues = _validate_contract(CONFIG_SPECS)
    rows: list[CheckRow] = []

    for key in sorted(CONFIG_SPECS):
        spec = CONFIG_SPECS[key]
        if spec.source == "db-dynamic":
            row, spec_issues = _analyze_dynamic_spec(spec, db_map)
        else:
            row, spec_issues = _analyze_env_only_spec(spec)
        rows.append(row)
        issues.extend(spec_issues)

    known_db_keys = _collect_known_db_keys(CONFIG_SPECS)
    unknown_db_keys = sorted(set(db_map.keys()) - known_db_keys)
    for db_key in unknown_db_keys:
        issues.append(
            Issue(
                severity="P2",
                code="UNTRACKED_DB_KEY",
                key=db_key,
                message="该 DB 键未在配置契约中声明",
            )
        )

    sorted_issues = _sort_issues(issues)
    _print_summary(rows, sorted_issues, unknown_db_keys)
    _print_rows(rows, show_all=args.show_all)
    _print_issues(sorted_issues)

    if args.strict:
        has_blocking_issue = any(issue.severity in {"P0", "P1"} for issue in sorted_issues)
        return 1 if has_blocking_issue else 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
