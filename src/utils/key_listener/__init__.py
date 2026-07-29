"""API lắng nghe input và đọc NumLock theo hệ điều hành.

File path: `src/utils/key_listener/__init__.py`.
Input: timeout chờ event, stop event tùy chọn hoặc lời gọi đọc trạng thái NumLock.
Output: generator keyboard/mouse event đã chuẩn hóa và trạng thái NumLock `bool`.
Nguyên lý: facade chọn backend Linux hoặc Windows khi import; dependency native chỉ
được nạp khi listener bắt đầu hoặc NumLock được đọc.
"""

import sys

from utils.key_listener.types import KeyEvent, KeyState, MouseEvent, MouseState

if sys.platform == "win32":
    from utils.key_listener.window import get_num_lock_state, listen_keys, listen_mice
elif sys.platform.startswith("linux"):
    from utils.key_listener.linux import get_num_lock_state, listen_keys, listen_mice
else:
    raise NotImplementedError(f"Unsupported OS: {sys.platform}")

__all__ = [
    "KeyEvent",
    "KeyState",
    "MouseEvent",
    "MouseState",
    "get_num_lock_state",
    "listen_keys",
    "listen_mice",
]
