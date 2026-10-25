#!/usr/bin/env python
# @FileName  : log_rename.py
# @Project   : ODPlatform
# @Function  : 推理结束后把日志名对齐到输出目录(便于"现场 ⇄ 日志"互相找得到)
"""日志改名.

推理的现场目录是跑完才定的(runs/<task>_infer/<name>), 日志却在进程启动时就建好了.
跑完后把日志改成 "<output_dir 名>_<模型stem>.log", 让现场和日志一眼对上.
失败只 warn —— 日志名不值得让一次推理失败.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT_LOGGER_NAME = "od_platform"


def _find_file_handlers(logger_name: str = ROOT_LOGGER_NAME) -> list[logging.FileHandler]:
    """找到项目根 logger 上挂的 FileHandler(只读, 不动 handler 本身)。"""
    root = logging.getLogger(logger_name)
    return [h for h in root.handlers if isinstance(h, logging.FileHandler)]


def rename_log_to_save_dir(output_dir: Path, model_stem: str) -> Path | None:
    """把当前日志文件改名到 "<output_dir.name>_<model_stem>.log"。返回新路径。"""
    handlers = _find_file_handlers()
    if not handlers:
        return None

    handler = handlers[0]
    old_path = Path(handler.baseFilename)
    new_path = old_path.with_name(f"{Path(output_dir).name}_{model_stem}.log")
    if old_path == new_path or not old_path.exists():
        return old_path if old_path.exists() else None

    try:
        handler.close()                     # 先关流, Windows 上不关改不了名
        old_path.replace(new_path)
        handler.baseFilename = str(new_path)     # 让后续日志继续写新文件
        handler.stream = handler._open()         # noqa: SLF001 - 重开流是标准做法
        logger.info("日志已改名对齐输出目录: %s", new_path)
        return new_path
    except Exception as e:                  # noqa: BLE001 - 改名失败不影响推理结果
        logger.warning("日志改名失败 (已吞): %s", e)
        return old_path
