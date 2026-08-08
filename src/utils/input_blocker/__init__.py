"""Facade chặn/mở chặn input theo hệ điều hành hiện tại.

File path: `src/utils/input_blocker/__init__.py`
Input: `block()` và `unblock()` không nhận tham số.
Output: gọi platform service để chặn hoặc mở chặn bàn phím/chuột hiện tại.

Nguyên lý hoạt động: facade giữ public API cũ và lấy adapter mặc định từ Agent.
Linux dùng evdev; Windows dùng `BlockInput` từ user32 sau platform boundary.
"""

from agent.platform_protocols import InputBlockingOperations
from agent.platform import get_default_platform_services


def _get_operations() -> InputBlockingOperations:
    return get_default_platform_services().input_blocker


def block() -> None:
    """Chặn input qua adapter platform mặc định."""

    _get_operations().block()


def unblock() -> None:
    """Mở chặn input qua adapter platform mặc định."""

    _get_operations().unblock()

__all__ = ["block", "unblock"]
