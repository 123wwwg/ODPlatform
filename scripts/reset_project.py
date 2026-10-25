#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : scripts/reset_project.py
# @Author    : ODPlatform Team
# @Function  : 项目重置的【开发阶段入口】(无需安装 package)
#
# 用法:
#   python scripts/reset_project.py
"""ODPlatform 项目重置入口(开发阶段)"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "platform" / "src"))

from od_platform.cli.reset_project import main      # ← 调 main,不是 reset_project

if __name__ == "__main__":
    sys.exit(main())
