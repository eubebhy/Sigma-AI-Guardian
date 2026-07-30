"""Facade Windows cho gửi sự kiện bàn phím và chuột.

File path: `src/agent/platform/windows/input_controller/__init__.py`.
Input: lời gọi theo contract chung của input controller.
Output: API sender có cùng chữ ký với backend Linux.
Nguyên lý: chỉ re-export các module con; dependency nền tảng được import lazy bên
trong từng API để package vẫn import được trên Linux. Listener nằm tại
`utils.key_listener`.
"""

from agent.platform.windows.input_controller.sendinput_kb import (
    keyDown,
    keyUp,
    press,
    supportedKeys,
    supportedWriteCharacters,
    write,
)
from agent.platform.windows.input_controller.sendinput_mouse import (
    click,
    mouseDown,
    mouseUp,
    moveRel,
    moveTo,
    position,
    scroll,
    sideScroll,
)

__all__ = [
    "click",
    "keyDown",
    "keyUp",
    "mouseDown",
    "mouseUp",
    "moveRel",
    "moveTo",
    "position",
    "press",
    "scroll",
    "sideScroll",
    "supportedKeys",
    "supportedWriteCharacters",
    "write",
]
