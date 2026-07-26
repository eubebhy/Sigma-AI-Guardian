"""API gửi input độc lập hệ điều hành theo tập con tương thích PyAutoGUI.

File path: `src/utils/input_controller/__init__.py`.
Input: lời gọi gửi keyboard hoặc mouse với tham số theo PyAutoGUI.
Output: API gửi và lắng nghe input của backend phù hợp với hệ điều hành đang chạy.
Nguyên lý: facade chọn Linux hoặc Windows lúc import; mỗi backend tự nạp dependency
khi cần gửi event. Listener được giữ trong các module backend riêng.
"""

import sys

if sys.platform == "win32":
    from utils.input_controller.window import (
        click,
        get_num_lock_state,
        keyDown,
        keyUp,
        listen_keys,
        listen_mice,
        moveRel,
        moveTo,
        press,
        write,
    )
elif sys.platform.startswith("linux"):
    from utils.input_controller.linux import (
        click,
        get_num_lock_state,
        keyDown,
        keyUp,
        listen_keys,
        listen_mice,
        moveRel,
        moveTo,
        press,
        write,
    )
else:
    raise NotImplementedError(f"Unsupported OS: {sys.platform}")
from utils.input_controller.types import KeyEvent, MouseEvent


__all__ = [
    "KeyEvent",
    "MouseEvent",
    "click",
    "get_num_lock_state",
    "keyDown",
    "keyUp",
    "listen_keys",
    "listen_mice",
    "moveRel",
    "moveTo",
    "press",
    "write",
]
