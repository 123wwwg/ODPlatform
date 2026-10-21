#!/usr/bin/env python
# @FileName  : scripts/reset_project.py
# @Function  : 项目重置的【开发阶段入口】(无需安装 package)
"""ODPlatform 项目重置入口(开发阶段)"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "platform" / "src"))

from od_platform.cli.reset_project import main  # noqa: E402  ← 调 main,不是 reset_project

if __name__ == "__main__":
    sys.exit(main())
