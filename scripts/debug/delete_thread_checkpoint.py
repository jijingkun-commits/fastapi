#!/usr/bin/env python3
"""删除指定 thread 的 LangGraph checkpoint。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db.postgres_checkpoint import delete_thread_checkpoint


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="删除指定 thread 的 LangGraph checkpoint")
    parser.add_argument("--thread-id", required=True, help="要清理的 thread_id")
    return parser


async def _main() -> int:
    args = _build_parser().parse_args()
    result = await delete_thread_checkpoint(args.thread_id)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
