"""Backend điều khiển input Linux theo tập con API PyAutoGUI.

File path: `src/device_controler/input_controller/linux/__init__.py`.
Input: lời gọi sender chuẩn hóa từ facade package cha.
Output: API sender dùng virtual evdev/UInput.
Nguyên lý: module chỉ re-export sender; listener nằm tại `utils.key_listener`.
"""

from device_controler.input_controller.linux.sendinput_kb import (
    keyDown,
    keyUp,
    press,
    supportedKeys,
    supportedWriteCharacters,
    write,
)
from device_controler.input_controller.linux.sendinput_mouse import (
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
