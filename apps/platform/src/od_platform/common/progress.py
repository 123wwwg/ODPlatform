"""按运行隔离的进度开关；库调用默认安静，CLI 显式开启。"""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TypeVar

from tqdm import tqdm

_ENABLED = ContextVar("odp_progress_enabled", default=False)
_T = TypeVar("_T")


@contextmanager
def progress_reporting(enabled: bool) -> Iterator[None]:
    token = _ENABLED.set(enabled)
    try:
        yield
    finally:
        _ENABLED.reset(token)


def iter_progress(
    items: Iterable[_T], description: str, *, total: int | None = None
) -> Iterator[_T]:
    if not _ENABLED.get():
        yield from items
        return
    # 上下文确保异常/中断时也会关闭终端进度条。tqdm 默认写 stderr。
    with tqdm(items, desc=description, total=total, unit="item", dynamic_ncols=True) as bar:
        yield from bar
