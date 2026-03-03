"""Cursor 配置同步脚本：同步到 Claude Code 与 Codex。

同步五类文件：
0. Guide: AGENTS.md -> CLAUDE.md（自动镜像，禁止手改 CLAUDE.md）
1. Rules: .cursor/rules/*.mdc -> .claude/rules/*.md（去 frontmatter，下划线转连字符）
2. Commands: .cursor/commands/*.md -> .claude/commands/*.md（直接复制，替代 symlink）
3. Commands: .cursor/commands/*.md -> ~/.codex/prompts/*.md（由 ENABLE_PROMPT_REGISTRY_V2 控制 symlink/copy）
4. Skills: .cursor/commands/jjk-*.md -> .agents/skills/jjk-*/SKILL.md（不注入 prompt 注册）

用法:
    python scripts/sync_rules_to_cc.py          # 同步 rules + commands
    python scripts/sync_rules_to_cc.py --only rules
    python scripts/sync_rules_to_cc.py --only commands
    python scripts/sync_rules_to_cc.py --exclude banking-context
    python scripts/sync_rules_to_cc.py --skip-codex-prompts
    python scripts/sync_rules_to_cc.py --skip-jjk-skills
    python scripts/sync_rules_to_cc.py --codex-prompts-dir ~/.codex/prompts
"""

import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Optional, Set

# 项目根目录（兼容 symlink：脚本实体在 .cursor/scripts/，需向上三级）
_script_path = Path(__file__).resolve()
if _script_path.parent.parent.name == ".cursor":
    ROOT = _script_path.parent.parent.parent
else:
    ROOT = _script_path.parent.parent

CURSOR_RULES_DIR = ROOT / ".cursor" / "rules"
CLAUDE_RULES_DIR = ROOT / ".claude" / "rules"
CURSOR_COMMANDS_DIR = ROOT / ".cursor" / "commands"
CLAUDE_COMMANDS_DIR = ROOT / ".claude" / "commands"
AGENT_SKILLS_DIR = ROOT / ".agents" / "skills"
AGENTS_GUIDE_FILE = ROOT / "AGENTS.md"
CLAUDE_GUIDE_FILE = ROOT / "CLAUDE.md"
CLAUDE_GUIDE_MARKER = "<!-- AUTO-GENERATED FROM AGENTS.md via scripts/sync_rules_to_cc.py. DO NOT EDIT. -->"
SKILL_MIRROR_MARKER = "<!-- AUTO-GENERATED: jjk-skill-mirror -->"
DEFAULT_CODEX_PROMPTS_DIR = Path.home() / ".codex" / "prompts"
CODEX_MANIFEST_FILENAME = ".cursor_commands_manifest.json"
TEAM_BRIDGE_PREFIX = "jjk-team-"
TEAM_BRIDGE_MARKER = "<!-- AUTO-GENERATED: jjk-team-bridge -->"
TEAM_DEFAULT_ROLE = "planner"
TEAM_BRIDGE_EXCLUDED_STEMS = {"jjk-clarify", "jjk-plan", "jjk-pc"}
TEAM_BRIDGE_ENABLED_FLAG = "ENABLE_TEAM_BRIDGE_COMMANDS"
DISABLED_COMMAND_STEMS = {
    "jjk-diagrams",
    "jjk-error-handling",
    "jjk-migration",
    "jjk-optimize",
}
RULESET_V2_FLAG = "ENABLE_RULESET_V2"
PROMPT_REGISTRY_V2_FLAG = "ENABLE_PROMPT_REGISTRY_V2"
CLAUDE_RULES_V1_SNAPSHOT_DIR = ROOT / ".claude" / ".rules_v1_snapshot"

# frontmatter 正则：匹配文件开头的 --- ... --- 块
FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)


def strip_frontmatter(content: str) -> str:
    """去除 MDC 文件开头的 frontmatter 块。"""
    return FRONTMATTER_RE.sub("", content).lstrip("\n")


def _env_flag(name: str, default: bool = False) -> bool:
    """读取布尔环境变量。"""

    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _render_claude_guide_from_agents(agents_content: str) -> str:
    """将 AGENTS 内容渲染为 CLAUDE 镜像内容。"""

    lines = agents_content.splitlines()
    if lines:
        lines[0] = lines[0].replace("（Codex 版）", "（Claude 镜像）")

    for idx, line in enumerate(lines):
        if line.startswith("本文件是 Codex 在 "):
            lines[idx] = "本文件由 `AGENTS.md` 自动镜像生成，供 Claude Code 使用。"
            break

    body = "\n".join(lines).rstrip() + "\n"
    return f"{CLAUDE_GUIDE_MARKER}\n\n{body}"


def sync_claude_guide() -> bool:
    """同步 AGENTS 到 CLAUDE，返回是否发生更新。"""

    if not AGENTS_GUIDE_FILE.exists():
        print(f"警告: 未找到 AGENTS 源文件（{AGENTS_GUIDE_FILE}），跳过 CLAUDE 镜像同步")
        return False

    agents_content = AGENTS_GUIDE_FILE.read_text(encoding="utf-8")
    rendered = _render_claude_guide_from_agents(agents_content)
    current = ""
    if CLAUDE_GUIDE_FILE.exists():
        current = CLAUDE_GUIDE_FILE.read_text(encoding="utf-8")

    if current == rendered:
        return False

    CLAUDE_GUIDE_FILE.write_text(rendered, encoding="utf-8")
    return True


def mdc_to_md_name(mdc_name: str) -> str:
    """将 .mdc 文件名转换为 .md 文件名（下划线转连字符）。"""
    stem = Path(mdc_name).stem
    return stem.replace("_", "-") + ".md"


def _sha1_file(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def _extract_frontmatter_description(path: Path) -> str:
    """读取命令 frontmatter 的 description 字段（若存在）。"""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    if not content.startswith("---\n"):
        return ""
    lines = content.splitlines()
    for line in lines[1:40]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.startswith("description:"):
            return stripped.split(":", 1)[1].strip()
    return ""


def _team_role_for_command(stem: str) -> str:
    """根据命令名给出 team 角色建议。"""
    if stem in {"jjk-plan", "jjk-clarify", "jjk-vkplan"}:
        return "planner"
    if stem in {"jjk-imp", "jjk-imp-ws", "jjk-feature", "jjk-quick", "jjk-refactor"}:
        return "executor"
    if stem in {"jjk-debug", "jjk-pc"}:
        return "debugger"
    if stem in {"jjk-review"}:
        return "code-reviewer"
    if stem in {"jjk-test"}:
        return "test-engineer"
    if stem in {"jjk-verify"}:
        return "verifier"
    if stem in {"jjk-security-audit"}:
        return "security-reviewer"
    if stem in {"jjk-doc-check", "jjk-api-docs"}:
        return "writer"
    if stem in {"jjk-git-commit", "jjk-create-pr"}:
        return "git-master"
    return TEAM_DEFAULT_ROLE


def _collect_jjk_command_specs() -> list[dict[str, str]]:
    specs = []
    for cmd_file in sorted(CURSOR_COMMANDS_DIR.glob("jjk-*.md")):
        stem = cmd_file.stem
        if stem.startswith("jjk-team-"):
            continue
        if stem in TEAM_BRIDGE_EXCLUDED_STEMS:
            continue
        suffix = stem.removeprefix("jjk-")
        specs.append(
            {
                "stem": stem,
                "suffix": suffix,
                "file": cmd_file.name,
                "sha1": _sha1_file(cmd_file),
                "sha8": _sha1_file(cmd_file)[:8],
                "description": _extract_frontmatter_description(cmd_file) or "-",
                "role": _team_role_for_command(stem),
                "team_file": f"{TEAM_BRIDGE_PREFIX}{suffix}.md",
            }
        )
    return specs


def _render_team_bridge_command(spec: dict[str, str]) -> str:
    stem = spec["stem"]
    suffix = spec["suffix"]
    source_file = spec["file"]
    role = spec["role"]
    source_sha1 = spec["sha1"]
    source_sha8 = spec["sha8"]
    team_file = spec["team_file"]
    description = spec["description"]
    return f"""---
description: Team 封装命令：执行 /prompts:{stem}（自动同步源命令）
---
{TEAM_BRIDGE_MARKER}
<!-- source: {source_file} -->
<!-- source_sha1: {source_sha1} -->

# Team 命令封装（`/{team_file.removesuffix(".md")}`）

将 `/{stem}` 封装为 Team 入口，且始终以源命令文档为唯一真理源。

## 使用方式

在命令后可选补充：

1. `workers=<N>`（默认建议 5）
2. `role=<agent_type>`（默认建议 `{role}`）
3. `mode=ralph|team`（默认建议 `ralph`）
4. 任务正文（你希望 AI 完成什么）

示例：

```text
/{team_file.removesuffix(".md")} workers=5 role={role} mode=ralph
任务：<在这里写你的任务目标>
```

## 执行协议（强制）

1. 先读取源文件：`.cursor/commands/{source_file}`，严格沿用其约束与产物要求。
2. 以 Team 方式组织执行，并显式执行：`/prompts:{stem}`。
3. 禁止把 `/{stem}` 当普通文本描述。
4. 每一步回传：`命令原文 + 产物绝对路径 + 校验结果(PASS/FAIL)`。

## 源命令元数据（自动同步）

| 字段 | 值 |
|---|---|
| source | `.cursor/commands/{source_file}` |
| source_sha8 | `{source_sha8}` |
| actual_prompt | `/prompts:{stem}` |
| recommended_role | `{role}` |
| description | {description} |

## 同步机制

本文件由 `python3 scripts/sync_rules_to_cc.py --only commands` 自动生成。

当 `.cursor/commands/{source_file}` 变更后，重新执行同步脚本即可自动刷新本文件，并同步到：

1. `.claude/commands/{team_file}`（CC 端）
2. `~/.codex/prompts/{team_file}`（Codex 端）
"""


def ensure_team_bridge_commands() -> list[str]:
    """为每个 /jjk-xxx 自动生成 /jjk-team-xxx 命令。"""
    if not CURSOR_COMMANDS_DIR.exists():
        return []
    specs = _collect_jjk_command_specs()
    generated: list[str] = []

    for spec in specs:
        team_name = spec["team_file"]
        generated.append(team_name)
        target = CURSOR_COMMANDS_DIR / team_name
        rendered = _render_team_bridge_command(spec)
        current = ""
        if target.exists():
            try:
                current = target.read_text(encoding="utf-8")
            except OSError:
                current = ""
        if current != rendered:
            target.write_text(rendered, encoding="utf-8")

    generated_set = set(generated)
    for existing in CURSOR_COMMANDS_DIR.glob(f"{TEAM_BRIDGE_PREFIX}*.md"):
        if existing.name in generated_set:
            continue
        try:
            content = existing.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if TEAM_BRIDGE_MARKER in content:
            existing.unlink()

    return generated


def cleanup_generated_team_bridge_commands() -> list[str]:
    """清理自动生成的 /jjk-team-* 桥接命令。"""
    if not CURSOR_COMMANDS_DIR.exists():
        return []

    removed: list[str] = []
    for existing in CURSOR_COMMANDS_DIR.glob(f"{TEAM_BRIDGE_PREFIX}*.md"):
        try:
            content = existing.read_text(encoding="utf-8")
        except OSError:
            content = ""
        if TEAM_BRIDGE_MARKER in content:
            existing.unlink()
            removed.append(existing.name)
    return removed


def cleanup_disabled_commands() -> list[str]:
    """清理被禁用的命令文件，防止误恢复。"""
    if not CURSOR_COMMANDS_DIR.exists():
        return []

    removed: list[str] = []
    for stem in sorted(DISABLED_COMMAND_STEMS):
        target = CURSOR_COMMANDS_DIR / f"{stem}.md"
        if not target.exists():
            continue
        target.unlink()
        removed.append(target.name)
    return removed


def prepare_team_bridge_commands() -> None:
    """根据开关生成或清理 Team 桥接命令。"""
    bridge_enabled = _env_flag(TEAM_BRIDGE_ENABLED_FLAG, default=False)
    print(f"[team-bridge] {TEAM_BRIDGE_ENABLED_FLAG}={str(bridge_enabled).lower()}")

    if bridge_enabled:
        ensure_team_bridge_commands()
        return

    removed = cleanup_generated_team_bridge_commands()
    if removed:
        print(f"  已清理 {len(removed)} 个自动生成的 team 命令。")


def sync_rules(exclude: Optional[Set[str]] = None) -> list[str]:
    """同步规则文件，返回生成的文件列表。"""
    exclude = exclude or set()
    CLAUDE_RULES_DIR.mkdir(parents=True, exist_ok=True)
    ruleset_v2_enabled = _env_flag(RULESET_V2_FLAG, default=False)
    print(f"[sync-rules] {RULESET_V2_FLAG}={str(ruleset_v2_enabled).lower()}")

    if ruleset_v2_enabled:
        _snapshot_current_rules_for_rollback()
    else:
        restored = _restore_rules_from_snapshot()
        if restored:
            expected_rules = {
                mdc_to_md_name(path.name)
                for path in CURSOR_RULES_DIR.glob("*.mdc")
                if path.stem not in exclude
            }
            restored_set = set(restored)
            missing_rules = sorted(expected_rules - restored_set)
            if missing_rules:
                print(
                    "警告: 当前处于 V1 回滚模式，以下 .cursor/rules 新规则未进入 .claude/rules："
                )
                for name in missing_rules:
                    print(f"  - {name}")
                print(f"如需同步新规则，请开启 {RULESET_V2_FLAG}=true 后再执行同步。")
            print(f"{RULESET_V2_FLAG}=false，已从快照恢复 V1 规则集。")
            return restored

    generated = []
    for mdc_file in sorted(CURSOR_RULES_DIR.glob("*.mdc")):
        stem = mdc_file.stem
        if stem in exclude:
            continue

        out_name = mdc_to_md_name(mdc_file.name)
        content = mdc_file.read_text(encoding="utf-8")
        cleaned = strip_frontmatter(content)
        out_path = CLAUDE_RULES_DIR / out_name
        out_path.write_text(cleaned, encoding="utf-8")
        generated.append(out_name)

    # 清理孤儿文件
    generated_set = set(generated)
    for existing in CLAUDE_RULES_DIR.glob("*.md"):
        if existing.name not in generated_set:
            existing.unlink()
            print(f"  清理孤儿规则: {existing.name}")

    return generated


def _snapshot_current_rules_for_rollback() -> None:
    """在首次启用规则集 V2 时，为回滚保留 V1 快照。"""

    if CLAUDE_RULES_V1_SNAPSHOT_DIR.exists():
        existing = list(CLAUDE_RULES_V1_SNAPSHOT_DIR.glob("*.md"))
        if existing:
            return

    CLAUDE_RULES_V1_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for rule_file in CLAUDE_RULES_DIR.glob("*.md"):
        shutil.copy2(rule_file, CLAUDE_RULES_V1_SNAPSHOT_DIR / rule_file.name)


def _restore_rules_from_snapshot() -> list[str]:
    """规则集 V2 关闭时恢复 V1 快照。

    返回已恢复的规则文件名列表；若无快照则返回空列表。
    """

    if not CLAUDE_RULES_V1_SNAPSHOT_DIR.exists():
        return []

    snapshot_files = sorted(CLAUDE_RULES_V1_SNAPSHOT_DIR.glob("*.md"))
    if not snapshot_files:
        return []

    CLAUDE_RULES_DIR.mkdir(parents=True, exist_ok=True)
    for existing in CLAUDE_RULES_DIR.glob("*.md"):
        existing.unlink()

    restored: list[str] = []
    for snapshot_file in snapshot_files:
        target = CLAUDE_RULES_DIR / snapshot_file.name
        shutil.copy2(snapshot_file, target)
        restored.append(snapshot_file.name)
    return restored


def sync_commands() -> list[str]:
    """同步命令文件（直接复制），返回同步的文件列表。"""
    if not CURSOR_COMMANDS_DIR.exists():
        return []
    removed_disabled = cleanup_disabled_commands()
    if removed_disabled:
        print(f"  已清理 {len(removed_disabled)} 个禁用命令: {', '.join(removed_disabled)}")
    prepare_team_bridge_commands()
    CLAUDE_COMMANDS_DIR.mkdir(parents=True, exist_ok=True)

    synced = []
    for cmd_file in sorted(CURSOR_COMMANDS_DIR.glob("*.md")):
        dest = CLAUDE_COMMANDS_DIR / cmd_file.name
        # 如果目标是 symlink，先删除再复制
        if dest.is_symlink():
            dest.unlink()
        shutil.copy2(cmd_file, dest)
        synced.append(cmd_file.name)

    # 清理孤儿命令
    synced_set = set(synced)
    for existing in CLAUDE_COMMANDS_DIR.glob("*.md"):
        if existing.is_symlink():
            existing.unlink()
            print(f"  清理残留 symlink: {existing.name}")
        elif existing.name not in synced_set:
            existing.unlink()
            print(f"  清理孤儿命令: {existing.name}")

    return synced


def _read_codex_manifest(manifest_path: Path) -> Set[str]:
    """读取 Codex 命令镜像 manifest。"""
    if not manifest_path.exists():
        return set()
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    files = data.get("managed_files", [])
    return {name for name in files if isinstance(name, str)}


def _write_codex_manifest(manifest_path: Path, managed_files: list[str]) -> None:
    """写入 Codex 命令镜像 manifest。"""
    payload = {"managed_files": managed_files}
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sync_commands_to_codex(codex_prompts_dir: Path) -> list[str]:
    """同步命令到 Codex prompts 目录。"""
    if not CURSOR_COMMANDS_DIR.exists():
        return []
    removed_disabled = cleanup_disabled_commands()
    if removed_disabled:
        print(f"  已清理 {len(removed_disabled)} 个禁用命令: {', '.join(removed_disabled)}")
    prepare_team_bridge_commands()
    codex_prompts_dir.mkdir(parents=True, exist_ok=True)
    registry_v2_enabled = _env_flag(PROMPT_REGISTRY_V2_FLAG, default=False)
    mode = "symlink" if registry_v2_enabled else "copy"
    print(f"[sync-prompts] {PROMPT_REGISTRY_V2_FLAG}={str(registry_v2_enabled).lower()} mode={mode}")

    synced = []
    for cmd_file in sorted(CURSOR_COMMANDS_DIR.glob("*.md")):
        dest = codex_prompts_dir / cmd_file.name
        if registry_v2_enabled:
            source_abs = cmd_file.resolve()
            rel_target = Path(os.path.relpath(source_abs, codex_prompts_dir))

            if dest.is_symlink():
                current_target = Path(os.readlink(dest))
                if current_target == rel_target:
                    synced.append(cmd_file.name)
                    continue
                dest.unlink()
            elif dest.exists():
                dest.unlink()

            try:
                dest.symlink_to(rel_target)
            except OSError:
                shutil.copy2(cmd_file, dest)
        else:
            if dest.is_symlink():
                dest.unlink()
            shutil.copy2(cmd_file, dest)
        synced.append(cmd_file.name)

    manifest_path = codex_prompts_dir / CODEX_MANIFEST_FILENAME
    previous_files = _read_codex_manifest(manifest_path)
    current_files = set(synced)

    for orphan in sorted(previous_files - current_files):
        orphan_path = codex_prompts_dir / orphan
        if orphan_path.exists() or orphan_path.is_symlink():
            orphan_path.unlink()
            print(f"  清理 Codex 孤儿命令: {orphan}")

    _write_codex_manifest(manifest_path, sorted(current_files))
    return synced


def _skill_description_for_command(stem: str, source_description: str) -> str:
    """生成 Skill frontmatter description。"""
    desc = " ".join(source_description.split())
    if desc:
        return f"Use when you need `{stem}` in this repository. Source intent: {desc}"
    return f"Use when you need `{stem}` in this repository."


def _command_body_to_skill_body(stem: str, content: str) -> str:
    """将命令正文转换为 Skill 正文。"""
    body = FRONTMATTER_RE.sub("", content).lstrip("\n")

    body = re.sub(
        r"(?<![\w-])/prompts:(jjk-[a-z0-9-]+)",
        lambda m: f"${m.group(1)}",
        body,
    )
    body = re.sub(
        r"(?<![\w-])/(jjk-[a-z0-9-]+)",
        lambda m: f"${m.group(1)}",
        body,
    )

    body = body.replace(
        "Codex 的自定义命令入口是 `/prompts:<name>`，不是 `/<name>`。",
        f"Codex 推荐显式调用 `${stem}`。",
    )

    return body.rstrip() + "\n"


def _render_skill_markdown(stem: str, source_file: str, source_description: str, content: str) -> str:
    """渲染 SKILL.md 内容。"""
    skill_desc = _skill_description_for_command(stem, source_description)
    body = _command_body_to_skill_body(stem=stem, content=content)
    quoted_desc = json.dumps(skill_desc, ensure_ascii=False)

    return (
        f"---\n"
        f"name: {stem}\n"
        f"description: {quoted_desc}\n"
        f"---\n"
        f"{SKILL_MIRROR_MARKER}\n"
        f"<!-- source: .cursor/commands/{source_file} -->\n\n"
        f"{body}"
    )


def sync_jjk_command_skills() -> list[str]:
    """将 .cursor/commands/jjk-*.md 镜像为 .agents/skills/jjk-*/SKILL.md。"""
    if not CURSOR_COMMANDS_DIR.exists():
        return []

    AGENT_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    managed: list[str] = []

    for cmd_file in sorted(CURSOR_COMMANDS_DIR.glob("jjk-*.md")):
        stem = cmd_file.stem
        if stem.startswith("jjk-team-"):
            continue

        source_content = cmd_file.read_text(encoding="utf-8")
        source_desc = _extract_frontmatter_description(cmd_file)
        skill_dir = AGENT_SKILLS_DIR / stem
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_md = skill_dir / "SKILL.md"
        rendered_md = _render_skill_markdown(
            stem=stem,
            source_file=cmd_file.name,
            source_description=source_desc,
            content=source_content,
        )
        current_md = skill_md.read_text(encoding="utf-8") if skill_md.exists() else ""
        if current_md != rendered_md:
            skill_md.write_text(rendered_md, encoding="utf-8")

        agents_dir = skill_dir / "agents"
        openai_yaml = agents_dir / "openai.yaml"
        if openai_yaml.exists():
            current_yaml = openai_yaml.read_text(encoding="utf-8")
            if SKILL_MIRROR_MARKER in current_yaml:
                openai_yaml.unlink()
                if agents_dir.exists() and not any(agents_dir.iterdir()):
                    agents_dir.rmdir()

        managed.append(stem)

    managed_set = set(managed)
    for skill_dir in sorted(AGENT_SKILLS_DIR.glob("jjk-*")):
        if skill_dir.name in managed_set or not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        content = skill_md.read_text(encoding="utf-8")
        if SKILL_MIRROR_MARKER in content:
            shutil.rmtree(skill_dir)
            print(f"  清理 JJK 孤儿技能: {skill_dir.name}")

    return managed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="同步 Cursor 规则和命令到 Claude Code / Codex"
    )
    parser.add_argument(
        "--exclude",
        default="",
        help="排除的规则文件名（逗号分隔，不含后缀）",
    )
    parser.add_argument(
        "--only",
        choices=["rules", "commands"],
        default=None,
        help="只同步指定类型（默认两者都同步）",
    )
    parser.add_argument(
        "--skip-codex-prompts",
        action="store_true",
        help="跳过同步到 Codex prompts（~/.codex/prompts）",
    )
    parser.add_argument(
        "--codex-prompts-dir",
        default=str(DEFAULT_CODEX_PROMPTS_DIR),
        help="Codex prompts 目录（默认: ~/.codex/prompts）",
    )
    parser.add_argument(
        "--skip-jjk-skills",
        action="store_true",
        help="跳过将 .cursor/commands/jjk-*.md 同步为 .agents/skills",
    )
    args = parser.parse_args()

    exclude = {s.strip() for s in args.exclude.split(",") if s.strip()}

    guide_changed = sync_claude_guide()
    if guide_changed:
        print(f"已同步 CLAUDE 指南镜像: {CLAUDE_GUIDE_FILE}")
    else:
        print(f"CLAUDE 指南镜像已是最新: {CLAUDE_GUIDE_FILE}")

    if args.only != "commands":
        rules = sync_rules(exclude=exclude)
        print(f"已同步 {len(rules)} 个规则文件到 {CLAUDE_RULES_DIR}/:")
        for name in rules:
            print(f"  - {name}")
        if exclude:
            print(f"已排除: {', '.join(sorted(exclude))}")

    if args.only != "rules":
        commands = sync_commands()
        print(f"已同步 {len(commands)} 个命令文件到 {CLAUDE_COMMANDS_DIR}/:")
        for name in commands:
            print(f"  - {name}")

        if args.skip_jjk_skills:
            print("已跳过 JJK Skill 同步（--skip-jjk-skills）")
        else:
            jjk_skills = sync_jjk_command_skills()
            print(f"已同步 {len(jjk_skills)} 个 JJK Skill 到 {AGENT_SKILLS_DIR}/:")
            for name in jjk_skills:
                print(f"  - {name}")

        if args.skip_codex_prompts:
            print("已跳过 Codex prompts 同步（--skip-codex-prompts）")
        else:
            codex_prompts_dir = Path(args.codex_prompts_dir).expanduser()
            try:
                codex_commands = sync_commands_to_codex(codex_prompts_dir)
                print(f"已同步 {len(codex_commands)} 个命令文件到 {codex_prompts_dir}/:")
                for name in codex_commands:
                    print(f"  - {name}")
            except OSError as exc:
                print(f"警告: Codex prompts 同步失败（{codex_prompts_dir}）: {exc}")


if __name__ == "__main__":
    main()
