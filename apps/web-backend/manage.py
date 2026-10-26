#!/usr/bin/env python
from __future__ import annotations

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django 未安装。请在 ODP 环境执行: "
            'python -m pip install -e "./apps/web-backend"'
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
