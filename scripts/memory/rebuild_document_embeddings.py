#!/usr/bin/env python3
"""文档记忆向量补偿脚本（中文注释）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.db.session import get_db_context  # noqa: E402
from app.services import document_memory_embedding_service  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="文档记忆向量补偿任务")
    parser.add_argument("--limit", type=int, default=200, help="本次处理上限（默认 200）")
    parser.add_argument("--user-id", type=int, default=None, help="仅处理指定用户")
    parser.add_argument("--doc-id", type=int, default=None, help="仅处理指定文档")
    parser.add_argument(
        "--status",
        dest="status_filter",
        default="pending,failed",
        help="待处理状态，逗号分隔（默认 pending,failed）",
    )
    parser.add_argument(
        "--max-retry",
        type=int,
        default=document_memory_embedding_service.DEFAULT_MAX_RETRY,
        help="自动重试上限（默认 3）",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    status_filter = [
        item.strip().lower()
        for item in str(args.status_filter or "").split(",")
        if item.strip()
    ]

    with get_db_context() as db:
        summary = document_memory_embedding_service.process_pending_chunks(
            db,
            limit=max(1, int(args.limit)),
            user_id=args.user_id,
            doc_id=args.doc_id,
            status_filter=status_filter,
            max_retry=max(0, int(args.max_retry)),
        )

    print(json.dumps(summary, ensure_ascii=False))
    return 0 if int(summary.get("failed", 0)) == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
