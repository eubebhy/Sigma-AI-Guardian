"""API điều khiển input độc lập hệ điều hành theo tập con PyAutoGUI.

File path: `src/device_controler/input_controller/__init__.py`.
Input: lời gọi gửi keyboard hoặc mouse với tham số theo PyAutoGUI.
Output: API gửi input của backend phù hợp với hệ điều hành đang chạy.
Nguyên lý: facade chọn Linux hoặc Windows lúc import; mỗi backend tự nạp dependency
khi cần gửi event. Listener nằm ở `utils.key_listener`.
"""

import sys

if sys.platform == "win32":
    from device_controler.input_controller.window import (
        click,
        keyDown,
        keyUp,
        moveRel,
        moveTo,
        mouseDown,
        mouseUp,
        press,
        position,
        scroll,
        sideScroll,
        supportedKeys,
        supportedWriteCharacters,
        write,
    )
elif sys.platform.startswith("linux"):
    from device_controler.input_controller.linux import (
        click,
        keyDown,
        keyUp,
        moveRel,
        moveTo,
        mouseDown,
        mouseUp,
        press,
        position,
        scroll,
        sideScroll,
        supportedKeys,
        supportedWriteCharacters,
        write,
    )
else:
    raise NotImplementedError(f"Unsupported OS: {sys.platform}")


__all__ = [
    "click",
    "keyDown",
    "keyUp",
    "moveRel",
    "moveTo",
    "mouseDown",
    "mouseUp",
    "press",
    "position",
    "scroll",
    "sideScroll",
    "supportedKeys",
    "supportedWriteCharacters",
    "write",
]
