"""技能服务：管理 Agent Skills 的导入、同步和检索（中文注释）。"""

import ast
import hashlib
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.ai.utils.embedding_util import get_embedding
from app.core.config import SKILL_SIMILARITY_THRESHOLD
from app.db.session import get_db_context
from app.models.agent_skill import AgentSkill
from app.services.system_config_service import SystemConfigService

logger = logging.getLogger(__name__)


class SkillService:
    """技能管理服务。"""

    DEFAULT_SCOPE = "global"
    DEFAULT_PRIORITY = 100
    PRIORITY_MIN = 0
    PRIORITY_MAX = 10000
    VALID_SCOPES = {DEFAULT_SCOPE, "data", "todo", "admin"}
    FRONTMATTER_ALIASES = {
        "name": ("name",),
        "description": ("description",),
        "scope": ("scope",),
        "priority": ("priority",),
        "auto_enabled": ("auto_enabled", "auto-enabled", "autoEnabled"),
        "is_enabled": ("is_enabled", "is-enabled", "enabled"),
        "trigger_phrases": ("trigger_phrases", "trigger-phrases"),
        "conflicts_with": ("conflicts_with", "conflicts-with"),
    }

    @staticmethod
    def _compute_file_hash(content: str) -> str:
        """计算内容 MD5。"""

        return hashlib.md5(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _format_warning(field: str, message: str, raw_value: Any = None) -> str:
        """构造字段级 warning 文本，便于日志检索。"""

        if raw_value is None:
            return f"field={field} message={message}"

        normalized = str(raw_value).strip().replace("\n", "\\n")
        if len(normalized) > 80:
            normalized = f"{normalized[:77]}..."
        return f"field={field} value={normalized!r} message={message}"

    @staticmethod
    def _get_frontmatter_value(frontmatter: Dict[str, Any], aliases: Tuple[str, ...]) -> Tuple[Any, bool]:
        """按别名顺序读取 frontmatter 字段值。"""

        for alias in aliases:
            if alias in frontmatter:
                return frontmatter[alias], True
        return None, False

    @classmethod
    def _parse_legacy_frontmatter(cls, frontmatter_text: str) -> Dict[str, Any]:
        """兼容旧版逐行解析，作为非法 YAML 的降级兜底。"""

        parsed: Dict[str, Any] = {}
        for line in frontmatter_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue

            key, raw_value = stripped.split(":", 1)
            parsed[key.strip()] = raw_value.strip().strip("\"'")

        return parsed

    @classmethod
    def _load_frontmatter(cls, frontmatter_text: str) -> Tuple[Dict[str, Any], str, List[str]]:
        """解析 frontmatter，返回结构化结果、状态与 warning。"""

        if not frontmatter_text.strip():
            return {}, "valid", []

        warnings: List[str] = []
        try:
            loaded = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as exc:
            fallback = cls._parse_legacy_frontmatter(frontmatter_text)
            warnings.append(
                cls._format_warning(
                    "frontmatter",
                    "YAML 解析失败，已按宽松模式降级",
                    exc.__class__.__name__,
                )
            )
            return fallback, "invalid", warnings

        if loaded is None:
            return {}, "valid", warnings

        if isinstance(loaded, dict):
            return loaded, "valid", warnings

        warnings.append(
            cls._format_warning(
                "frontmatter",
                "顶层结构必须是对象，已忽略",
                type(loaded).__name__,
            )
        )
        return {}, "invalid", warnings

    @staticmethod
    def _parse_list_value(raw_value: Any) -> Tuple[List[str], bool]:
        """将 frontmatter 中的列表字段解析为字符串列表。"""

        if raw_value is None:
            return [], True

        parsed: Any = raw_value
        parse_ok = True

        if isinstance(parsed, str):
            value = parsed.strip()
            if not value:
                return [], True

            parsed = value
            if value.startswith("[") and value.endswith("]"):
                try:
                    parsed = ast.literal_eval(value)
                except (SyntaxError, ValueError):
                    parse_ok = False
                    parsed = value

        if isinstance(parsed, (list, tuple, set)):
            values = [str(item).strip() for item in parsed if str(item).strip()]
            return list(dict.fromkeys(values)), parse_ok

        if isinstance(parsed, str):
            if "," in parsed:
                values = [item.strip() for item in parsed.split(",") if item.strip()]
                return list(dict.fromkeys(values)), parse_ok
            return ([parsed] if parsed else []), parse_ok

        return [], False

    @staticmethod
    def _parse_bool_value(raw_value: Any, default: bool = True) -> Tuple[bool, bool]:
        """解析 frontmatter 布尔值。"""

        if isinstance(raw_value, bool):
            return raw_value, True

        if isinstance(raw_value, (int, float)) and raw_value in {0, 1}:
            return bool(raw_value), True

        if isinstance(raw_value, str):
            value = raw_value.strip().lower()
            if value in {"true", "1", "yes", "on"}:
                return True, True
            if value in {"false", "0", "no", "off"}:
                return False, True

        return default, False

    @staticmethod
    def _parse_int_value(
        raw_value: Any,
        default: int = DEFAULT_PRIORITY,
        min_value: int = PRIORITY_MIN,
        max_value: int = PRIORITY_MAX,
    ) -> Tuple[int, bool]:
        """解析 frontmatter 整数值。"""

        try:
            value = int(str(raw_value).strip())
        except (TypeError, ValueError):
            return default, False

        if value < min_value or value > max_value:
            return default, False

        return value, True

    @classmethod
    def _normalize_scope(cls, raw_value: Any, default: str = DEFAULT_SCOPE) -> Tuple[str, bool]:
        """标准化作用域值。"""

        if raw_value is None:
            return default, True

        normalized = str(raw_value).strip().lower()
        if not normalized:
            return default, True

        if normalized not in cls.VALID_SCOPES:
            return default, False

        return normalized, True

    @classmethod
    def _parse_skill_file(cls, skill_path: Path) -> Optional[dict]:
        """解析 SKILL.md 文件，提取元数据和内容。"""

        if not skill_path.exists():
            return None

        content = skill_path.read_text(encoding="utf-8")
        skill_id = skill_path.parent.name

        warnings: List[str] = []
        frontmatter_status = "missing"

        name = skill_id.replace("-", " ").title()
        description = ""
        scope = cls.DEFAULT_SCOPE
        priority = cls.DEFAULT_PRIORITY
        auto_enabled = True
        is_enabled = True
        trigger_phrases: List[str] = []
        conflicts_with: List[str] = []

        body_content = content
        frontmatter_data: Dict[str, Any] = {}

        lines = content.splitlines()
        if lines and lines[0].strip() == "---":
            end_idx = -1
            for idx, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    end_idx = idx
                    break

            if end_idx > 0:
                frontmatter_text = "\n".join(lines[1:end_idx])
                body_content = "\n".join(lines[end_idx + 1 :])
                frontmatter_data, frontmatter_status, frontmatter_warnings = cls._load_frontmatter(frontmatter_text)
                warnings.extend(frontmatter_warnings)
            else:
                frontmatter_status = "invalid"
                warnings.append(
                    cls._format_warning(
                        "frontmatter",
                        "缺少结束分隔符，已按默认值回退",
                    )
                )

        name_value, has_name = cls._get_frontmatter_value(frontmatter_data, cls.FRONTMATTER_ALIASES["name"])
        if has_name:
            normalized_name = str(name_value).strip()
            if normalized_name:
                name = normalized_name
            else:
                warnings.append(
                    cls._format_warning(
                        "name",
                        "值为空，已回退为目录名",
                        name_value,
                    )
                )

        description_value, has_description = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["description"],
        )
        if has_description:
            normalized_description = str(description_value).strip()
            if normalized_description:
                description = normalized_description
            else:
                warnings.append(
                    cls._format_warning(
                        "description",
                        "值为空，已回退为正文摘要",
                        description_value,
                    )
                )

        scope_value, has_scope = cls._get_frontmatter_value(frontmatter_data, cls.FRONTMATTER_ALIASES["scope"])
        if has_scope:
            scope, valid_scope = cls._normalize_scope(scope_value, default=cls.DEFAULT_SCOPE)
            if not valid_scope:
                warnings.append(
                    cls._format_warning(
                        "scope",
                        f"仅支持 {sorted(cls.VALID_SCOPES)}，已回退默认值",
                        scope_value,
                    )
                )

        priority_value, has_priority = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["priority"],
        )
        if has_priority:
            priority, valid_priority = cls._parse_int_value(
                priority_value,
                default=cls.DEFAULT_PRIORITY,
                min_value=cls.PRIORITY_MIN,
                max_value=cls.PRIORITY_MAX,
            )
            if not valid_priority:
                warnings.append(
                    cls._format_warning(
                        "priority",
                        f"需为 {cls.PRIORITY_MIN}-{cls.PRIORITY_MAX} 的整数，已回退默认值",
                        priority_value,
                    )
                )

        auto_enabled_value, has_auto_enabled = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["auto_enabled"],
        )
        if has_auto_enabled:
            auto_enabled, valid_auto_enabled = cls._parse_bool_value(auto_enabled_value, default=True)
            if not valid_auto_enabled:
                warnings.append(
                    cls._format_warning(
                        "auto_enabled",
                        "需为布尔值，已回退默认值 true",
                        auto_enabled_value,
                    )
                )

        is_enabled_value, has_is_enabled = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["is_enabled"],
        )
        if has_is_enabled:
            is_enabled, valid_is_enabled = cls._parse_bool_value(is_enabled_value, default=True)
            if not valid_is_enabled:
                warnings.append(
                    cls._format_warning(
                        "is_enabled",
                        "需为布尔值，已回退默认值 true",
                        is_enabled_value,
                    )
                )

        trigger_phrases_value, has_trigger_phrases = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["trigger_phrases"],
        )
        if has_trigger_phrases:
            trigger_phrases, valid_trigger_phrases = cls._parse_list_value(trigger_phrases_value)
            if not valid_trigger_phrases:
                warnings.append(
                    cls._format_warning(
                        "trigger_phrases",
                        "需为字符串列表或逗号分隔字符串，已回退为空数组",
                        trigger_phrases_value,
                    )
                )

        conflicts_with_value, has_conflicts_with = cls._get_frontmatter_value(
            frontmatter_data,
            cls.FRONTMATTER_ALIASES["conflicts_with"],
        )
        if has_conflicts_with:
            parsed_conflicts, valid_conflicts_with = cls._parse_list_value(conflicts_with_value)
            if not valid_conflicts_with:
                warnings.append(
                    cls._format_warning(
                        "conflicts_with",
                        "需为字符串列表或逗号分隔字符串，已回退为空数组",
                        conflicts_with_value,
                    )
                )
            conflicts_with = list(
                dict.fromkeys([item.strip().lower() for item in parsed_conflicts if item and item.strip()])
            )

            if skill_id in conflicts_with:
                conflicts_with = [item for item in conflicts_with if item != skill_id]
                warnings.append(
                    cls._format_warning(
                        "conflicts_with",
                        "包含自身 skill_id，已自动移除",
                        skill_id,
                    )
                )

        if not description:
            clean_content = re.sub(r"^#+\s*", "", body_content, flags=re.MULTILINE).strip()
            description = clean_content[:200] if len(clean_content) > 200 else clean_content

        if warnings and frontmatter_status == "valid":
            frontmatter_status = "invalid"

        return {
            "skill_id": skill_id,
            "name": name,
            "description": description,
            "content": content,
            "scope": scope,
            "priority": priority,
            "auto_enabled": auto_enabled,
            "is_enabled": is_enabled,
            "trigger_phrases": trigger_phrases,
            "conflicts_with": conflicts_with,
            "frontmatter_status": frontmatter_status,
            "warnings": warnings,
        }

    @classmethod
    def import_skill(cls, skill_path: Path, db: Session, force: bool = False) -> bool:
        """导入单个技能到数据库。"""

        parsed = cls._parse_skill_file(skill_path)
        if not parsed:
            return False

        skill_id = parsed["skill_id"]

        for warning in parsed.get("warnings", []):
            logger.warning("技能 %s frontmatter 字段异常: %s", skill_id, warning)

        frontmatter_status = parsed.get("frontmatter_status")
        if frontmatter_status == "missing":
            logger.debug("技能 %s 未声明 frontmatter，使用默认元数据", skill_id)
        elif frontmatter_status == "invalid":
            logger.warning("技能 %s frontmatter 存在非法或降级字段，已按回退策略导入", skill_id)

        content = parsed["content"]
        file_hash = cls._compute_file_hash(content)

        existing = db.execute(
            select(AgentSkill).where(AgentSkill.skill_id == skill_id)
        ).scalar_one_or_none()

        if existing:
            if not force and existing.file_hash == file_hash:
                logger.debug("技能 %s 未变化，跳过", skill_id)
                return False

            existing.name = parsed["name"]
            existing.description = parsed["description"]
            existing.content = content
            existing.file_hash = file_hash
            existing.embedding = get_embedding(parsed["description"])
            existing.scope = parsed["scope"]
            existing.priority = parsed["priority"]
            existing.auto_enabled = parsed["auto_enabled"]
            existing.is_enabled = parsed["is_enabled"]
            existing.trigger_phrases = parsed["trigger_phrases"]
            existing.conflicts_with = parsed["conflicts_with"]
            logger.info("更新技能: %s", skill_id)
        else:
            embedding = get_embedding(parsed["description"])
            skill = AgentSkill(
                skill_id=skill_id,
                name=parsed["name"],
                description=parsed["description"],
                content=content,
                file_hash=file_hash,
                embedding=embedding,
                scope=parsed["scope"],
                priority=parsed["priority"],
                auto_enabled=parsed["auto_enabled"],
                is_enabled=parsed["is_enabled"],
                trigger_phrases=parsed["trigger_phrases"],
                conflicts_with=parsed["conflicts_with"],
            )
            db.add(skill)
            logger.info("导入技能: %s", skill_id)

        db.commit()
        return True

    @classmethod
    def import_all_skills(
        cls,
        skills_dir: Path,
        force: bool = False,
        whitelist: Optional[List[str]] = None,
    ) -> int:
        """从目录导入所有技能。"""

        if not skills_dir.exists():
            logger.warning("技能目录不存在: %s", skills_dir)
            return 0

        updated_count = 0
        skipped_count = 0
        failed_count = 0
        skill_files = sorted(skills_dir.glob("*/SKILL.md"), key=lambda path: path.parent.name)

        if whitelist:
            whitelist_set = set(whitelist)
            skill_files = [f for f in skill_files if f.parent.name in whitelist_set]
            logger.info("应用白名单过滤: %s", whitelist)

        logger.info("发现 %d 个技能文件", len(skill_files))

        with get_db_context() as db:
            for skill_path in skill_files:
                try:
                    if cls.import_skill(skill_path, db, force):
                        updated_count += 1
                    else:
                        skipped_count += 1
                except Exception as exc:  # pragma: no cover - 仅记录日志
                    failed_count += 1
                    db.rollback()
                    logger.exception(
                        "导入技能失败 skill_id=%s path=%s error=%s",
                        skill_path.parent.name,
                        skill_path,
                        exc,
                    )

        logger.info(
            "技能导入完成: 总数=%d, 更新=%d, 跳过=%d, 失败=%d",
            len(skill_files),
            updated_count,
            skipped_count,
            failed_count,
        )

        return updated_count

    @classmethod
    def sync_changed_skills(cls, skills_dir: Path) -> int:
        """同步变化的技能（增量更新）。"""

        return cls.import_all_skills(skills_dir, force=False)

    @staticmethod
    def _normalize_score(raw_score: Optional[float]) -> float:
        """归一化分数到 0-1。"""

        if raw_score is None:
            return 0.0
        return max(0.0, min(1.0, float(raw_score)))

    @staticmethod
    def _scope_matched(skill_scope: Optional[str], request_scope: str) -> bool:
        """判断技能作用域是否匹配。"""

        normalized_skill_scope = (skill_scope or SkillService.DEFAULT_SCOPE).strip().lower()
        normalized_request_scope = (request_scope or SkillService.DEFAULT_SCOPE).strip().lower()

        if normalized_request_scope in {"", SkillService.DEFAULT_SCOPE}:
            return True

        return normalized_skill_scope in {SkillService.DEFAULT_SCOPE, normalized_request_scope}

    @staticmethod
    def _tokenize_query(query: str) -> List[str]:
        """提取查询关键词。"""

        tokens: List[str] = []
        for raw_token in re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9_]+", query):
            token = raw_token.lower()
            tokens.append(token)

            if re.fullmatch(r"[\u4e00-\u9fff]+", token) and len(token) >= 3:
                for idx in range(len(token) - 1):
                    tokens.append(token[idx : idx + 2])
                if len(token) >= 4:
                    for idx in range(len(token) - 2):
                        tokens.append(token[idx : idx + 3])

        # 去重后保持顺序，减少重复匹配开销
        return list(dict.fromkeys(tokens))

    @classmethod
    def _split_markdown_sections(cls, content: str) -> List[Tuple[str, str]]:
        """按 Markdown 标题切分技能内容。"""

        sections: List[Tuple[str, str]] = []
        current_title = "概要"
        buffer: List[str] = []

        for line in content.splitlines():
            if line.startswith("#"):
                if buffer:
                    body = "\n".join(buffer).strip()
                    if body:
                        sections.append((current_title, body))
                current_title = line.lstrip("#").strip() or "未命名章节"
                buffer = []
            else:
                buffer.append(line)

        if buffer:
            body = "\n".join(buffer).strip()
            if body:
                sections.append((current_title, body))

        if not sections and content.strip():
            sections.append(("内容", content.strip()))

        return sections

    @classmethod
    def _pick_sections(cls, content: str, query: str, max_sections: int) -> List[Tuple[str, str]]:
        """按查询相关性选择章节。"""

        sections = cls._split_markdown_sections(content)
        if not sections:
            return []

        tokens = cls._tokenize_query(query)
        if not tokens:
            return sections[:max_sections]

        scored: List[Tuple[int, int, str, str]] = []
        for idx, (title, body) in enumerate(sections):
            haystack = f"{title}\n{body}".lower()
            score = sum(1 for token in tokens if token in haystack)
            scored.append((score, -idx, title, body))

        scored.sort(reverse=True)
        selected = [(title, body) for score, _, title, body in scored if score > 0]
        if not selected:
            selected = sections

        return selected[:max_sections]

    @classmethod
    def _build_skill_fragment_with_meta(
        cls,
        skill: AgentSkill,
        query: str,
        max_sections: int = 2,
    ) -> Tuple[str, int]:
        """生成单个技能的章节级上下文片段，并返回命中章节数。"""

        selected_sections = cls._pick_sections(skill.content or "", query=query, max_sections=max_sections)
        if not selected_sections:
            fallback = f"### {skill.name}\n{(skill.description or '').strip()}\n"
            return fallback, 1 if (skill.description or "").strip() else 0

        parts: List[str] = []
        for section_title, body in selected_sections:
            snippet = body.strip()
            if len(snippet) > 400:
                snippet = f"{snippet[:400]}..."
            parts.append(f"### {skill.name} · {section_title}\n{snippet}\n")

        return "\n".join(parts), len(selected_sections)

    @classmethod
    def _build_skill_fragment(cls, skill: AgentSkill, query: str, max_sections: int = 2) -> str:
        """生成单个技能的章节级上下文片段。"""

        fragment, _ = cls._build_skill_fragment_with_meta(skill, query=query, max_sections=max_sections)
        return fragment

    @classmethod
    def _fetch_vector_candidates(
        cls,
        db: Session,
        query_embedding: List[float],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """召回向量候选。"""

        sql = text(
            """
            SELECT
                id,
                skill_id,
                name,
                description,
                content,
                is_enabled,
                auto_enabled,
                priority,
                scope,
                trigger_phrases,
                conflicts_with,
                1 - (embedding <=> CAST(:query_vec AS vector)) AS vector_score
            FROM t_agent_skills
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:query_vec AS vector)
            LIMIT :limit
            """
        )

        rows = db.execute(sql, {"query_vec": query_embedding, "limit": limit})
        candidates: List[Dict[str, Any]] = []
        for row in rows:
            candidates.append(
                {
                    "id": row.id,
                    "skill_id": row.skill_id,
                    "name": row.name,
                    "description": row.description,
                    "content": row.content,
                    "is_enabled": row.is_enabled,
                    "auto_enabled": row.auto_enabled,
                    "priority": row.priority,
                    "scope": row.scope,
                    "trigger_phrases": row.trigger_phrases or [],
                    "conflicts_with": row.conflicts_with or [],
                    "vector_score": cls._normalize_score(row.vector_score),
                    "lexical_score": 0.0,
                    "trigger_hit": 0.0,
                }
            )
        return candidates

    @classmethod
    def _fetch_lexical_candidates(
        cls,
        db: Session,
        query: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """召回关键词候选。"""

        sql = text(
            """
            SELECT
                id,
                skill_id,
                name,
                description,
                content,
                is_enabled,
                auto_enabled,
                priority,
                scope,
                trigger_phrases,
                conflicts_with,
                ts_rank_cd(
                    to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(description, '') || ' ' || coalesce(content, '')),
                    plainto_tsquery('simple', :query)
                ) AS lexical_score,
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM jsonb_array_elements_text(trigger_phrases) AS phrase
                        WHERE lower(:raw_query) LIKE '%' || lower(phrase) || '%'
                    ) THEN 1.0
                    ELSE 0.0
                END AS trigger_hit
            FROM t_agent_skills
            WHERE
                to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(description, '') || ' ' || coalesce(content, ''))
                @@ plainto_tsquery('simple', :query)
                OR EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements_text(trigger_phrases) AS phrase
                    WHERE lower(:raw_query) LIKE '%' || lower(phrase) || '%'
                )
            ORDER BY lexical_score DESC, priority ASC
            LIMIT :limit
            """
        )

        rows = db.execute(sql, {"query": query, "raw_query": query.lower(), "limit": limit})
        candidates: List[Dict[str, Any]] = []
        for row in rows:
            candidates.append(
                {
                    "id": row.id,
                    "skill_id": row.skill_id,
                    "name": row.name,
                    "description": row.description,
                    "content": row.content,
                    "is_enabled": row.is_enabled,
                    "auto_enabled": row.auto_enabled,
                    "priority": row.priority,
                    "scope": row.scope,
                    "trigger_phrases": row.trigger_phrases or [],
                    "conflicts_with": row.conflicts_with or [],
                    "vector_score": 0.0,
                    "lexical_score": max(0.0, float(row.lexical_score or 0.0)),
                    "trigger_hit": cls._normalize_score(row.trigger_hit),
                }
            )
        return candidates

    @classmethod
    def _merge_candidates(
        cls,
        vector_candidates: List[Dict[str, Any]],
        lexical_candidates: List[Dict[str, Any]],
        mode: str,
    ) -> List[Dict[str, Any]]:
        """合并向量和关键词候选。"""

        merged: Dict[str, Dict[str, Any]] = {}

        for candidate in vector_candidates + lexical_candidates:
            skill_id = candidate["skill_id"]
            if skill_id not in merged:
                merged[skill_id] = candidate.copy()
                continue

            existing = merged[skill_id]
            existing["vector_score"] = max(existing.get("vector_score", 0.0), candidate.get("vector_score", 0.0))
            existing["lexical_score"] = max(existing.get("lexical_score", 0.0), candidate.get("lexical_score", 0.0))
            existing["trigger_hit"] = max(existing.get("trigger_hit", 0.0), candidate.get("trigger_hit", 0.0))

        candidates = list(merged.values())
        max_lexical = max((item.get("lexical_score", 0.0) for item in candidates), default=0.0)

        vector_weight = SystemConfigService.get_float("skill.hybrid.vector_weight", 0.65)
        lexical_weight = SystemConfigService.get_float("skill.hybrid.lexical_weight", 0.25)
        trigger_weight = SystemConfigService.get_float("skill.hybrid.trigger_weight", 0.10)

        for item in candidates:
            lexical_score = item.get("lexical_score", 0.0)
            lexical_norm = (lexical_score / max_lexical) if max_lexical > 0 else 0.0
            item["lexical_score"] = cls._normalize_score(lexical_norm)
            item["vector_score"] = cls._normalize_score(item.get("vector_score", 0.0))
            item["trigger_hit"] = cls._normalize_score(item.get("trigger_hit", 0.0))

            if mode == "vector":
                item["final_score"] = item["vector_score"]
            else:
                item["final_score"] = cls._normalize_score(
                    vector_weight * item["vector_score"]
                    + lexical_weight * item["lexical_score"]
                    + trigger_weight * item["trigger_hit"]
                )

        candidates.sort(key=lambda x: (x.get("final_score", 0.0), -int(x.get("priority", 100))), reverse=True)
        return candidates

    @classmethod
    def _apply_policy_filters(
        cls,
        candidates: List[Dict[str, Any]],
        top_k: int,
        threshold: float,
        scope: str,
        auto_only: bool,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """执行启用状态、作用域和冲突裁决过滤。"""

        selected: List[Dict[str, Any]] = []
        dropped: List[Dict[str, Any]] = []

        ranked = sorted(
            candidates,
            key=lambda x: (x.get("final_score", 0.0), -int(x.get("priority", 100))),
            reverse=True,
        )

        for item in ranked:
            score = item.get("final_score", 0.0)
            trigger_hit = item.get("trigger_hit", 0.0)
            if score < threshold and trigger_hit < 1.0:
                dropped.append({"skill_id": item["skill_id"], "reason": "below_threshold", "score": round(score, 4)})
                continue

            if not item.get("is_enabled", True):
                dropped.append({"skill_id": item["skill_id"], "reason": "disabled"})
                continue

            if auto_only and not item.get("auto_enabled", True):
                dropped.append({"skill_id": item["skill_id"], "reason": "auto_disabled"})
                continue

            if not cls._scope_matched(item.get("scope"), scope):
                dropped.append({"skill_id": item["skill_id"], "reason": "scope_mismatch"})
                continue

            conflict_index = None
            for idx, selected_item in enumerate(selected):
                current_conflicts = {str(v) for v in (item.get("conflicts_with") or [])}
                selected_conflicts = {str(v) for v in (selected_item.get("conflicts_with") or [])}
                if item["skill_id"] in selected_conflicts or selected_item["skill_id"] in current_conflicts:
                    conflict_index = idx
                    break

            if conflict_index is None:
                selected.append(item)
                continue

            conflict_item = selected[conflict_index]
            current_priority = int(item.get("priority", 100))
            conflict_priority = int(conflict_item.get("priority", 100))
            current_score = float(item.get("final_score", 0.0))
            conflict_score = float(conflict_item.get("final_score", 0.0))

            if current_priority < conflict_priority or (
                current_priority == conflict_priority and current_score > conflict_score
            ):
                dropped.append(
                    {
                        "skill_id": conflict_item["skill_id"],
                        "reason": "conflict_replaced",
                        "replaced_by": item["skill_id"],
                    }
                )
                selected[conflict_index] = item
            else:
                dropped.append(
                    {
                        "skill_id": item["skill_id"],
                        "reason": "conflict",
                        "conflict_with": conflict_item["skill_id"],
                    }
                )

        selected.sort(
            key=lambda x: (x.get("final_score", 0.0), -int(x.get("priority", 100))),
            reverse=True,
        )
        if len(selected) > top_k:
            for overflow in selected[top_k:]:
                dropped.append({"skill_id": overflow["skill_id"], "reason": "top_k_overflow"})
            selected = selected[:top_k]

        return selected, dropped

    @classmethod
    def _search_skills_internal(
        cls,
        query: str,
        top_k: int,
        threshold: Optional[float],
        scope: str,
        auto_only: bool,
    ) -> Tuple[List[AgentSkill], Dict[str, Any]]:
        """统一检索入口，返回技能列表和调试信息。"""

        if not query.strip():
            return [], {"reason": "empty_query"}

        configured_top_k = SystemConfigService.get_int("skill.top_k", top_k)
        final_top_k = top_k if top_k > 0 else max(1, configured_top_k)

        base_threshold = (
            float(threshold)
            if threshold is not None
            else SystemConfigService.get_float("skill_similarity_threshold", SKILL_SIMILARITY_THRESHOLD)
        )
        retrieval_mode = SystemConfigService.get_string("skill.retrieval_mode", "hybrid").lower()
        candidate_multiplier = max(2, SystemConfigService.get_int("skill.hybrid.candidate_multiplier", 3))
        section_max_count = max(1, SystemConfigService.get_int("skill.section_max_count", 2))

        vector_candidates: List[Dict[str, Any]] = []
        lexical_candidates: List[Dict[str, Any]] = []

        query_embedding: Optional[List[float]] = None
        if retrieval_mode in {"hybrid", "vector"}:
            try:
                query_embedding = get_embedding(query)
            except Exception as exc:  # pragma: no cover - 外部依赖异常
                logger.warning("技能检索: 生成 embedding 失败，降级关键词检索 - %s", exc)
                query_embedding = None

        with get_db_context() as db:
            if query_embedding:
                try:
                    vector_candidates = cls._fetch_vector_candidates(
                        db,
                        query_embedding=query_embedding,
                        limit=final_top_k * candidate_multiplier,
                    )
                except Exception as exc:  # pragma: no cover - 数据库检索异常
                    logger.warning("技能检索: 向量召回失败，降级关键词检索 - %s", exc)
                    vector_candidates = []
            elif retrieval_mode == "vector":
                logger.warning("技能检索: vector 模式下 embedding 不可用，回退到 hybrid")
                retrieval_mode = "hybrid"

            if retrieval_mode == "hybrid" or not vector_candidates:
                try:
                    lexical_candidates = cls._fetch_lexical_candidates(
                        db,
                        query=query,
                        limit=final_top_k * candidate_multiplier,
                    )
                except Exception as exc:  # pragma: no cover - 数据库检索异常
                    logger.warning("技能检索: 关键词召回失败 - %s", exc)
                    lexical_candidates = []

        merged = cls._merge_candidates(vector_candidates, lexical_candidates, mode=retrieval_mode)
        effective_threshold = min(base_threshold, 0.35) if retrieval_mode == "hybrid" else base_threshold
        selected, dropped = cls._apply_policy_filters(
            merged,
            top_k=final_top_k,
            threshold=effective_threshold,
            scope=scope,
            auto_only=auto_only,
        )

        skills: List[AgentSkill] = []
        context_max_length = max(800, SystemConfigService.get_int("skill.context_max_length", 2400))

        for item in selected:
            skill = AgentSkill(
                id=item["id"],
                skill_id=item["skill_id"],
                name=item["name"],
                description=item.get("description"),
                content=item.get("content") or "",
                is_enabled=item.get("is_enabled", True),
                auto_enabled=item.get("auto_enabled", True),
                priority=item.get("priority", 100),
                scope=item.get("scope") or cls.DEFAULT_SCOPE,
                trigger_phrases=item.get("trigger_phrases") or [],
                conflicts_with=item.get("conflicts_with") or [],
            )
            skill._retrieval_score = item.get("final_score", 0.0)
            skill._vector_score = item.get("vector_score", 0.0)
            skill._lexical_score = item.get("lexical_score", 0.0)
            skill._trigger_hit = item.get("trigger_hit", 0.0)
            fragment, section_count = cls._build_skill_fragment_with_meta(
                skill,
                query=query,
                max_sections=section_max_count,
            )
            skill._lazy_context_fragment = fragment
            skill._lazy_section_count = section_count
            skills.append(skill)

        debug_info = {
            "query": query,
            "mode": retrieval_mode,
            "scope": scope,
            "threshold": base_threshold,
            "effective_threshold": effective_threshold,
            "vector_candidates": [
                {"skill_id": item["skill_id"], "vector_score": round(item.get("vector_score", 0.0), 4)}
                for item in vector_candidates[: min(10, len(vector_candidates))]
            ],
            "lexical_candidates": [
                {
                    "skill_id": item["skill_id"],
                    "lexical_score": round(item.get("lexical_score", 0.0), 4),
                    "trigger_hit": round(item.get("trigger_hit", 0.0), 4),
                }
                for item in lexical_candidates[: min(10, len(lexical_candidates))]
            ],
            "merged_candidates": [
                {
                    "skill_id": item["skill_id"],
                    "vector_score": round(item.get("vector_score", 0.0), 4),
                    "lexical_score": round(item.get("lexical_score", 0.0), 4),
                    "trigger_hit": round(item.get("trigger_hit", 0.0), 4),
                    "final_score": round(item.get("final_score", 0.0), 4),
                    "priority": item.get("priority", 100),
                    "scope": item.get("scope") or cls.DEFAULT_SCOPE,
                    "is_enabled": item.get("is_enabled", True),
                    "auto_enabled": item.get("auto_enabled", True),
                }
                for item in merged[: min(20, len(merged))]
            ],
            "final_candidates": [
                {
                    "skill_id": item["skill_id"],
                    "final_score": round(item.get("final_score", 0.0), 4),
                    "priority": item.get("priority", 100),
                }
                for item in selected
            ],
            "dropped": dropped,
            "selected_skill_ids": [item["skill_id"] for item in selected],
            "context_budget": context_max_length,
        }

        merged_preview = ", ".join(
            [
                f"{item['skill_id']}(f={item.get('final_score', 0.0):.3f},v={item.get('vector_score', 0.0):.3f},l={item.get('lexical_score', 0.0):.3f})"
                for item in merged[: min(6, len(merged))]
            ]
        )
        logger.info(
            "技能检索: mode=%s, scope=%s, 阈值=%.3f/%.3f, 候选=[%s], 入选=%s, 淘汰=%s",
            retrieval_mode,
            scope,
            base_threshold,
            effective_threshold,
            merged_preview,
            [item["skill_id"] for item in selected],
            dropped[:4],
        )

        return skills, debug_info

    @classmethod
    def search_skills(
        cls,
        query: str,
        top_k: int = 2,
        threshold: float = None,
        scope: str = DEFAULT_SCOPE,
        auto_only: bool = True,
    ) -> List[AgentSkill]:
        """检索相关技能（支持 hybrid/vector 策略）。"""

        skills, _ = cls._search_skills_internal(
            query=query,
            top_k=top_k,
            threshold=threshold,
            scope=scope,
            auto_only=auto_only,
        )
        return skills

    @classmethod
    def search_skills_debug(
        cls,
        query: str,
        top_k: int = 5,
        threshold: float = None,
        scope: str = DEFAULT_SCOPE,
        auto_only: bool = False,
    ) -> Dict[str, Any]:
        """检索技能并返回调试信息。"""

        skills, debug = cls._search_skills_internal(
            query=query,
            top_k=top_k,
            threshold=threshold,
            scope=scope,
            auto_only=auto_only,
        )

        context_budget = int(debug.get("context_budget") or 1200)
        context_preview, injection_meta = cls.format_skills_as_context_with_meta(skills, max_length=context_budget)

        results = [
            {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "description": skill.description,
                "score": round(float(getattr(skill, "_retrieval_score", 0.0)), 4),
                "vector_score": round(float(getattr(skill, "_vector_score", 0.0)), 4),
                "lexical_score": round(float(getattr(skill, "_lexical_score", 0.0)), 4),
                "trigger_hit": round(float(getattr(skill, "_trigger_hit", 0.0)), 4),
            }
            for skill in skills
        ]

        selected_skill_ids = [skill.skill_id for skill in skills]
        dropped_by_skill: Dict[str, List[Dict[str, Any]]] = {}
        for dropped_item in debug.get("dropped", []):
            skill_id = str(dropped_item.get("skill_id", "")).strip()
            if not skill_id:
                continue
            dropped_by_skill.setdefault(skill_id, []).append(dropped_item)

        merged_candidates = debug.get("merged_candidates", [])
        if merged_candidates:
            skill_candidates = [
                {
                    **candidate,
                    "selected": candidate.get("skill_id") in selected_skill_ids,
                    "drop_reasons": dropped_by_skill.get(candidate.get("skill_id", ""), []),
                }
                for candidate in merged_candidates
            ]
        else:
            skill_candidates = [
                {
                    "skill_id": item["skill_id"],
                    "vector_score": item["vector_score"],
                    "lexical_score": item["lexical_score"],
                    "trigger_hit": item["trigger_hit"],
                    "final_score": item["score"],
                    "selected": True,
                    "drop_reasons": [],
                }
                for item in results
            ]

        debug["results"] = results
        debug["count"] = len(skills)
        debug["context_preview"] = context_preview
        debug["skill_candidates"] = skill_candidates
        debug["selected_skill_ids"] = selected_skill_ids
        debug["skill_injection_meta"] = {
            **injection_meta,
            "mode": debug.get("mode"),
            "scope": debug.get("scope"),
            "top_k": top_k,
            "selected_count": len(selected_skill_ids),
        }
        return debug

    @classmethod
    def get_by_id(cls, skill_id: str) -> Optional[AgentSkill]:
        """根据 skill_id 获取技能。"""

        with get_db_context() as db:
            return db.execute(
                select(AgentSkill).where(AgentSkill.skill_id == skill_id)
            ).scalar_one_or_none()

    @classmethod
    def format_skills_as_context_with_meta(
        cls,
        skills: List[AgentSkill],
        max_length: int = 2000,
    ) -> Tuple[str, Dict[str, Any]]:
        """将技能列表格式化为注入上下文，并返回预算使用元信息。"""

        configured_max_length = SystemConfigService.get_int("skill.context_max_length", max_length)
        final_limit = min(max_length, configured_max_length) if max_length > 0 else configured_max_length
        if final_limit <= 0:
            final_limit = configured_max_length if configured_max_length > 0 else 2000

        if not skills:
            return "", {
                "budget_chars": final_limit,
                "used_chars": 0,
                "truncated": False,
                "included_skill_ids": [],
                "excluded_skill_ids": [],
                "sections_used": 0,
            }

        context_parts: List[str] = []
        total_length = 0
        sections_used = 0
        included_skill_ids: List[str] = []
        excluded_skill_ids: List[str] = []
        truncated = False

        for index, skill in enumerate(skills):
            fragment = getattr(skill, "_lazy_context_fragment", None)
            if not fragment:
                fragment, section_count = cls._build_skill_fragment_with_meta(
                    skill,
                    query=skill.description or "",
                    max_sections=1,
                )
            else:
                section_count = int(getattr(skill, "_lazy_section_count", 0) or 0)
                if section_count <= 0:
                    section_count = fragment.count("### ") or 1

            if total_length + len(fragment) > final_limit:
                truncated = True
                excluded_skill_ids.extend([item.skill_id for item in skills[index:]])
                break

            context_parts.append(fragment)
            total_length += len(fragment)
            sections_used += section_count
            included_skill_ids.append(skill.skill_id)

        return "\n".join(context_parts), {
            "budget_chars": final_limit,
            "used_chars": total_length,
            "truncated": truncated,
            "included_skill_ids": included_skill_ids,
            "excluded_skill_ids": excluded_skill_ids,
            "sections_used": sections_used,
        }

    @classmethod
    def format_skills_as_context(cls, skills: List[AgentSkill], max_length: int = 2000) -> str:
        """将技能列表格式化为注入上下文。"""

        context, _ = cls.format_skills_as_context_with_meta(skills, max_length=max_length)
        return context
