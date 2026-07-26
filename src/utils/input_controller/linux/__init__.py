"""Backend gửi input Linux theo tập con API PyAutoGUI.

File path: `src/utils/input_controller/linux/__init__.py`.
Input: lời gọi sender chuẩn hóa từ facade package cha.
Output: bảy hàm sender dùng virtual evdev/UInput.
Nguyên lý: module chỉ re-export sender; listener vẫn nằm tại `listener.py`.
"""

from utils.input_controller.linux.sendinput_kb import (
    keyDown,
    keyUp,
    press,
    supportedKeys,
    supportedWriteCharacters,
    write,
)
from utils.input_controller.linux.sendinput_mouse import (
    click,
    mouseDown,
    mouseUp,
    moveRel,
    moveTo,
    position,
    scroll,
    sideScroll,
)
from utils.input_controller.linux.listener import listen_keys, listen_mice

__all__ = [
    "click",
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
