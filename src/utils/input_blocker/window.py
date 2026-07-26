# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
"""Backend Windows để chặn input bằng Win32 `BlockInput`.

File path: `src/utils/input_blocker/window.py`
Input: `block()` và `unblock()` không nhận tham số.
Output: Windows bật/tắt trạng thái chặn input toàn hệ thống.

Nguyên lý hoạt động: gọi `user32.BlockInput(True/False)` qua `ctypes`. API này
thường yêu cầu quyền admin và có thể fail nếu process không đủ quyền.
"""

import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.BlockInput.argtypes = [wintypes.BOOL]
user32.BlockInput.restype = wintypes.BOOL


# Require admin
def _set_block_state(is_blocked: bool) -> None:
    if not user32.BlockInput(is_blocked):
        raise ctypes.WinError(ctypes.get_last_error())


def block() -> None:
    """Yêu cầu Windows chặn input người dùng."""

    _set_block_state(True)


def unblock() -> None:
    """Yêu cầu Windows mở chặn input người dùng."""

    _set_block_state(False)
