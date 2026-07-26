"""Facade Windows cho gửi và lắng nghe sự kiện bàn phím, chuột.

File path: `src/utils/input_controller/window/__init__.py`
Input: lời gọi theo contract chung của input controller.
Output: bảy API sender có cùng chữ ký với backend Linux.
Nguyên lý: chỉ re-export các module con; dependency nền tảng được import lazy bên
trong từng API để package vẫn import được trên Linux.
"""

from utils.input_controller.window.sendinput_kb import (
    get_num_lock_state,
    keyDown,
    keyUp,
    press,
    supportedKeys,
    supportedWriteCharacters,
    write,
)
from utils.input_controller.window.sendinput_mouse import (
    click,
    mouseDown,
    mouseUp,
    moveRel,
    moveTo,
    position,
    scroll,
    sideScroll,
)
from utils.input_controller.window.listener import listen_keys, listen_mice

__all__ = [
    "click",
    "get_num_lock_state",
    "keyDown",
    "keyUp",
    "listen_keys",
    "listen_mice",
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
