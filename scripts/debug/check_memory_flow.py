#!/usr/bin/env python3
"""记忆链路数据库诊断脚本（中文注释）。

用途：统一核对以下几张表，避免继续用旧口径误判“记忆没保存”。
- t_chat_message
- t_user_memory_document
- t_user_memory_chunk
- t_user_memory_intent_job
- t_user_memory

默认只读查询 chat_db，不改任何数据。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.config import DATABASE_URL  # noqa: E402

try:
    import psycopg  # noqa: E402
    from psycopg.rows import dict_row  # noqa: E402
except Exception as exc:  # pragma: no cover
    print(f"[FATAL] 无法导入 psycopg: {exc}", file=sys.stderr)
    sys.exit(2)


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_RUNTIME = 3


@dataclass
class DerivedConclusion:
    user_found: bool
    active_document_count: int
    archived_document_count: int
    matching_document_count: int
    chunk_count: int
    async_job_count: int
    legacy_kv_count: int
    memory_saved_to_document_db: bool
    memory_currently_active: bool
    memory_archived: bool
    likely_persist_path: str
    observation_summary: str


TABLE_SPECS: dict[str, tuple[str, ...]] = {
    "t_chat_message": (
        "id",
        "user_id",
        "thread_id",
        "role",
        "content",
        "create_time",
    ),
    "t_user_memory_document": (
        "id",
        "user_id",
        "doc_kind",
        "doc_key",
        "slot_key",
        "title",
        "status",
        "operation",
        "revision",
        "source",
        "source_thread_id",
        "source_message_id",
        "summary_md",
        "content_md",
        "create_time",
        "update_time",
    ),
    "t_user_memory_chunk": (
        "id",
        "doc_id",
        "user_id",
        "chunk_no",
        "start_line",
        "end_line",
        "chunk_text",
        "embedding_status",
        "create_time",
        "update_time",
    ),
    "t_user_memory_intent_job": (
        "id",
        "user_id",
        "source_thread_id",
        "source_message_id",
        "status",
        "attempt_count",
        "error_message",
        "payload_json",
        "create_time",
        "update_time",
    ),
    "t_user_memory": (
        "id",
        "user_id",
        "scope",
        "memory_key",
        "memory_value",
        "status",
        "source_thread_id",
        "source_message_id",
        "create_time",
        "update_time",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="统一诊断记忆写入/删除链路，优先核对 document memory 口径。",
    )
    user_group = parser.add_mutually_exclusive_group(required=True)
    user_group.add_argument("--user-id", type=int, help="用户 ID")
    user_group.add_argument("--username", help="用户名，例如 jjk")
    parser.add_argument(
        "--thread-id",
        action="append",
        default=[],
        help="线程 ID，可重复传入多次",
    )
    parser.add_argument(
        "--slot-key",
        help="槽位键，例如 user.profile.fact.favorite.color",
    )
    parser.add_argument(
        "--keyword",
        help="模糊关键字，例如 蓝色；会同时匹配消息、文档、chunk、旧 KV、任务载荷",
    )
    parser.add_argument(
        "--source-message-id",
        action="append",
        type=int,
        default=[],
        help="来源消息 ID，可重复传入多次",
    )
    parser.add_argument("--limit", type=int, default=20, help="每个查询分组的上限，默认 20")
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果，便于脚本消费")
    return parser.parse_args()


def normalize_conninfo(raw_url: str) -> str:
    return str(raw_url or "").replace("postgresql+psycopg://", "postgresql://", 1)


def clip_text(value: Any, max_len: int = 200) -> str:
    text = "" if value is None else str(value)
    compact = " ".join(text.split())
    if len(compact) <= max_len:
        return compact
    return f"{compact[: max_len - 1]}…"


def iso_or_empty(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    return str(value)


def table_exists(cur: Any, table_name: str) -> bool:
    cur.execute(
        """
        select 1
        from information_schema.tables
        where table_schema='public' and table_name=%s
        limit 1
        """,
        (table_name,),
    )
    return cur.fetchone() is not None


def resolve_user(cur: Any, user_id: int | None, username: str | None) -> dict[str, Any] | None:
    if user_id is not None:
        cur.execute(
            """
            select id, username, mobile, is_active, create_time
            from t_user
            where id = %s
            limit 1
            """,
            (user_id,),
        )
        return cur.fetchone()

    cur.execute(
        """
        select id, username, mobile, is_active, create_time
        from t_user
        where username = %s
        order by id desc
        limit 1
        """,
        (username,),
    )
    return cur.fetchone()


def fetch_messages(
    cur: Any,
    *,
    user_id: int,
    thread_ids: Sequence[str],
    keyword: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    conditions = ["user_id = %s"]
    params: list[Any] = [user_id]
    if thread_ids:
        conditions.append("thread_id = any(%s)")
        params.append(list(thread_ids))
    if keyword:
        conditions.append("content like %s")
        params.append(f"%{keyword}%")

    sql = f"""
        select id, user_id, thread_id, role, content, create_time
        from t_chat_message
        where {' and '.join(conditions)}
        order by id asc
        limit %s
    """
    params.append(limit)
    cur.execute(sql, params)
    return cur.fetchall()


def fetch_memory_documents(
    cur: Any,
    *,
    user_id: int,
    thread_ids: Sequence[str],
    source_message_ids: Sequence[int],
    slot_key: str | None,
    keyword: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    conditions = ["user_id = %s"]
    params: list[Any] = [user_id]
    if thread_ids:
        conditions.append("source_thread_id = any(%s)")
        params.append(list(thread_ids))
    if source_message_ids:
        conditions.append("source_message_id = any(%s)")
        params.append(list(source_message_ids))
    if slot_key:
        conditions.append("slot_key = %s")
        params.append(slot_key)
    if keyword:
        like_keyword = f"%{keyword}%"
        conditions.append(
            "(content_md like %s or coalesce(summary_md, '') like %s or coalesce(title, '') like %s or coalesce(slot_key, '') like %s)"
        )
        params.extend([like_keyword, like_keyword, like_keyword, like_keyword])

    sql = f"""
        select id, user_id, doc_kind, doc_key, slot_key, title, status, operation, revision,
               source, source_thread_id, source_message_id, summary_md, content_md,
               create_time, update_time
        from t_user_memory_document
        where {' and '.join(conditions)}
        order by id desc
        limit %s
    """
    params.append(limit)
    cur.execute(sql, params)
    return cur.fetchall()


def fetch_memory_chunks(cur: Any, *, doc_ids: Sequence[int], limit: int) -> list[dict[str, Any]]:
    if not doc_ids:
        return []
    cur.execute(
        """
        select id, doc_id, user_id, chunk_no, start_line, end_line, chunk_text,
               embedding_status, create_time, update_time
        from t_user_memory_chunk
        where doc_id = any(%s)
        order by id asc
        limit %s
        """,
        (list(doc_ids), limit),
    )
    return cur.fetchall()


def fetch_async_jobs(
    cur: Any,
    *,
    user_id: int,
    thread_ids: Sequence[str],
    source_message_ids: Sequence[int],
    keyword: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    conditions = ["user_id = %s"]
    params: list[Any] = [user_id]
    if thread_ids:
        conditions.append("source_thread_id = any(%s)")
        params.append(list(thread_ids))
    if source_message_ids:
        conditions.append("source_message_id = any(%s)")
        params.append(list(source_message_ids))
    if keyword:
        conditions.append("payload_json::text like %s")
        params.append(f"%{keyword}%")

    sql = f"""
        select id, user_id, source_thread_id, source_message_id, status, attempt_count,
               error_message, payload_json, create_time, update_time
        from t_user_memory_intent_job
        where {' and '.join(conditions)}
        order by id desc
        limit %s
    """
    params.append(limit)
    cur.execute(sql, params)
    return cur.fetchall()


def fetch_legacy_kv(
    cur: Any,
    *,
    user_id: int,
    thread_ids: Sequence[str],
    source_message_ids: Sequence[int],
    keyword: str | None,
    slot_key: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    conditions = ["user_id = %s"]
    params: list[Any] = [user_id]
    if thread_ids:
        conditions.append("source_thread_id = any(%s)")
        params.append(list(thread_ids))
    if source_message_ids:
        conditions.append("source_message_id = any(%s)")
        params.append(list(source_message_ids))
    if slot_key:
        conditions.append("memory_key = %s")
        params.append(slot_key)
    if keyword:
        conditions.append("(memory_key like %s or memory_value like %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    sql = f"""
        select id, user_id, scope, memory_key, memory_value, status,
               source_thread_id, source_message_id, create_time, update_time
        from t_user_memory
        where {' and '.join(conditions)}
        order by id desc
        limit %s
    """
    params.append(limit)
    cur.execute(sql, params)
    return cur.fetchall()


def build_conclusion(
    *,
    user_found: bool,
    documents: Sequence[dict[str, Any]],
    chunks: Sequence[dict[str, Any]],
    async_jobs: Sequence[dict[str, Any]],
    legacy_kv: Sequence[dict[str, Any]],
) -> DerivedConclusion:
    active_document_count = sum(1 for item in documents if str(item.get("status") or "") == "active")
    archived_document_count = sum(1 for item in documents if str(item.get("status") or "") == "archived")
    matching_document_count = len(documents)
    chunk_count = len(chunks)
    async_job_count = len(async_jobs)
    legacy_kv_count = len(legacy_kv)
    memory_saved_to_document_db = matching_document_count > 0
    memory_currently_active = active_document_count > 0
    memory_archived = archived_document_count > 0 and active_document_count == 0
    if memory_saved_to_document_db:
        likely_persist_path = "document_memory"
    elif async_job_count > 0:
        likely_persist_path = "memory_intent_async_queue_only"
    elif legacy_kv_count > 0:
        likely_persist_path = "legacy_user_memory_kv"
    else:
        likely_persist_path = "not_found"

    if not user_found:
        observation_summary = "未找到目标用户，无法判断记忆链路。"
    elif memory_currently_active:
        observation_summary = "目标记忆已保存且当前仍为 active，可继续被召回。"
    elif memory_archived:
        observation_summary = "目标记忆已进入 archived，符合“删除成功但保留归档痕迹”的设计。"
    elif memory_saved_to_document_db:
        observation_summary = "目标记忆已进入 document memory，但当前状态需要结合 status/operation 继续判读。"
    elif async_job_count > 0:
        observation_summary = "仅发现异步任务记录，尚未看到最终文档记忆结果。"
    else:
        observation_summary = "未在 document memory / async job / legacy kv 中找到匹配记录。"

    return DerivedConclusion(
        user_found=user_found,
        active_document_count=active_document_count,
        archived_document_count=archived_document_count,
        matching_document_count=matching_document_count,
        chunk_count=chunk_count,
        async_job_count=async_job_count,
        legacy_kv_count=legacy_kv_count,
        memory_saved_to_document_db=memory_saved_to_document_db,
        memory_currently_active=memory_currently_active,
        memory_archived=memory_archived,
        likely_persist_path=likely_persist_path,
        observation_summary=observation_summary,
    )


def render_rows(title: str, rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> str:
    lines = [f"\n## {title}"]
    if not rows:
        lines.append("- 无记录")
        return "\n".join(lines)

    for index, row in enumerate(rows, start=1):
        lines.append(f"- #{index}")
        for field in fields:
            value = row.get(field)
            if field in {"content", "content_md", "summary_md", "chunk_text", "memory_value", "payload_json"}:
                value = clip_text(value, max_len=220)
            elif field.endswith("_time"):
                value = iso_or_empty(value)
            lines.append(f"  - {field}: {value}")
    return "\n".join(lines)


def render_text_report(
    *,
    args: argparse.Namespace,
    user: dict[str, Any] | None,
    messages: Sequence[dict[str, Any]],
    documents: Sequence[dict[str, Any]],
    chunks: Sequence[dict[str, Any]],
    async_jobs: Sequence[dict[str, Any]],
    legacy_kv: Sequence[dict[str, Any]],
    conclusion: DerivedConclusion,
) -> str:
    lines = ["# 记忆链路诊断报告"]
    lines.append("\n## 输入参数")
    lines.append(f"- user_id: {args.user_id}")
    lines.append(f"- username: {args.username}")
    lines.append(f"- thread_ids: {args.thread_id}")
    lines.append(f"- slot_key: {args.slot_key}")
    lines.append(f"- keyword: {args.keyword}")
    lines.append(f"- source_message_ids: {args.source_message_id}")
    lines.append(f"- limit: {args.limit}")

    lines.append("\n## 用户")
    if user is None:
        lines.append("- 未找到用户")
    else:
        lines.append(f"- id: {user.get('id')}")
        lines.append(f"- username: {user.get('username')}")
        lines.append(f"- is_active: {user.get('is_active')}")
        lines.append(f"- create_time: {iso_or_empty(user.get('create_time'))}")

    lines.append("\n## 推导结论")
    for key, value in asdict(conclusion).items():
        lines.append(f"- {key}: {value}")

    lines.append(render_rows("聊天消息 t_chat_message", messages, TABLE_SPECS["t_chat_message"]))
    lines.append(
        render_rows(
            "文档记忆 t_user_memory_document",
            documents,
            TABLE_SPECS["t_user_memory_document"],
        )
    )
    lines.append(render_rows("文档分块 t_user_memory_chunk", chunks, TABLE_SPECS["t_user_memory_chunk"]))
    lines.append(
        render_rows(
            "异步任务 t_user_memory_intent_job",
            async_jobs,
            TABLE_SPECS["t_user_memory_intent_job"],
        )
    )
    lines.append(render_rows("旧 KV t_user_memory", legacy_kv, TABLE_SPECS["t_user_memory"]))
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    if args.limit <= 0:
        print("[FATAL] --limit 必须大于 0", file=sys.stderr)
        return EXIT_USAGE

    conninfo = normalize_conninfo(DATABASE_URL)
    try:
        with psycopg.connect(conninfo, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                user = resolve_user(cur, args.user_id, args.username)
                if user is None:
                    conclusion = build_conclusion(
                        user_found=False,
                        documents=[],
                        chunks=[],
                        async_jobs=[],
                        legacy_kv=[],
                    )
                    payload = {
                        "user": None,
                        "messages": [],
                        "documents": [],
                        "chunks": [],
                        "async_jobs": [],
                        "legacy_kv": [],
                        "conclusion": asdict(conclusion),
                    }
                    if args.json:
                        print(json.dumps(payload, ensure_ascii=False, default=iso_or_empty, indent=2))
                    else:
                        print(render_text_report(
                            args=args,
                            user=None,
                            messages=[],
                            documents=[],
                            chunks=[],
                            async_jobs=[],
                            legacy_kv=[],
                            conclusion=conclusion,
                        ))
                    return EXIT_OK

                user_id = int(user["id"])
                thread_ids = [item for item in args.thread_id if item]
                source_message_ids = [int(item) for item in args.source_message_id if item is not None]

                messages = fetch_messages(
                    cur,
                    user_id=user_id,
                    thread_ids=thread_ids,
                    keyword=args.keyword,
                    limit=args.limit,
                ) if table_exists(cur, "t_chat_message") else []

                documents = fetch_memory_documents(
                    cur,
                    user_id=user_id,
                    thread_ids=thread_ids,
                    source_message_ids=source_message_ids,
                    slot_key=args.slot_key,
                    keyword=args.keyword,
                    limit=args.limit,
                ) if table_exists(cur, "t_user_memory_document") else []

                chunks = fetch_memory_chunks(
                    cur,
                    doc_ids=[int(item["id"]) for item in documents],
                    limit=args.limit,
                ) if table_exists(cur, "t_user_memory_chunk") else []

                async_jobs = fetch_async_jobs(
                    cur,
                    user_id=user_id,
                    thread_ids=thread_ids,
                    source_message_ids=source_message_ids,
                    keyword=args.keyword,
                    limit=args.limit,
                ) if table_exists(cur, "t_user_memory_intent_job") else []

                legacy_kv = fetch_legacy_kv(
                    cur,
                    user_id=user_id,
                    thread_ids=thread_ids,
                    source_message_ids=source_message_ids,
                    keyword=args.keyword,
                    slot_key=args.slot_key,
                    limit=args.limit,
                ) if table_exists(cur, "t_user_memory") else []

                conclusion = build_conclusion(
                    user_found=True,
                    documents=documents,
                    chunks=chunks,
                    async_jobs=async_jobs,
                    legacy_kv=legacy_kv,
                )

                payload = {
                    "user": dict(user),
                    "messages": messages,
                    "documents": documents,
                    "chunks": chunks,
                    "async_jobs": async_jobs,
                    "legacy_kv": legacy_kv,
                    "conclusion": asdict(conclusion),
                }

                if args.json:
                    print(json.dumps(payload, ensure_ascii=False, default=iso_or_empty, indent=2))
                else:
                    print(
                        render_text_report(
                            args=args,
                            user=dict(user),
                            messages=messages,
                            documents=documents,
                            chunks=chunks,
                            async_jobs=async_jobs,
                            legacy_kv=legacy_kv,
                            conclusion=conclusion,
                        )
                    )
                return EXIT_OK
    except Exception as exc:
        print(f"[FATAL] 诊断失败: {exc}", file=sys.stderr)
        return EXIT_RUNTIME


if __name__ == "__main__":
    raise SystemExit(main())
