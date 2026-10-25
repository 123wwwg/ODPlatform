#!/usr/bin/env python
# @FileName  : cancel.py
# @Project   : ODPlatform
# @Function  : 线程安全的取消信号 (CancelToken)
"""推理取消信号.

GUI / Web 没有键盘按键, 需要程序化告诉 pipeline "该停了".
ThreadedPipeline 在主循环 4 个检查点查询 is_cancelled(), 收到信号优雅退出(<2s).
"""
from __future__ import annotations

import threading


class CancelToken:
    """线程安全的取消信号. 调用方持有, pipeline 只查不阻塞."""

    def __init__(self) -> None:
        self._evt = threading.Event()

    def cancel(self) -> None:
        """请求取消. 幂等."""
        self._evt.set()

    def is_cancelled(self) -> bool:
        """非阻塞查询."""
        return self._evt.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        """阻塞等待 cancel 信号."""
        return self._evt.wait(timeout)


class InferenceCancelled(Exception):
    """推理被主动取消(留给需要区分"用户取消/真错误"的业务方)."""
