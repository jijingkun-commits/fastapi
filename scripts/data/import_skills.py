#!/usr/bin/env python3
"""本地技能导入脚本已退役。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.skill_service import SkillService


def main() -> int:
    print(SkillService.LOCAL_SKILL_FILE_SOURCE_RETIRED_MESSAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
