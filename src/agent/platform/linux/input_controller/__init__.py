"""Backend điều khiển input Linux theo tập con API PyAutoGUI.

File path: `src/agent/platform/linux/input_controller/__init__.py`.
Input: lời gọi sender chuẩn hóa từ facade package cha.
Output: API sender dùng virtual evdev/UInput.
Nguyên lý: module chỉ re-export sender; listener nằm tại `utils.key_listener`.
"""

from agent.platform.linux.input_controller.sendinput_kb import (
    close as close_keyboard,
    keyDown,
    keyUp,
    press,
    supportedKeys,
    supportedWriteCharacters,
    write,
)
from agent.platform.linux.input_controller.sendinput_mouse import (
    close as close_mouse,
    click,
    mouseDown,
    mouseUp,
    moveRel,
    moveTo,
    position,
    scroll,
    sideScroll,
)


def close() -> None:
    """Đóng virtual keyboard, mouse và X11 resource đã cache."""

    errors: list[Exception] = []
    for cleanup in (close_keyboard, close_mouse):
        try:
            cleanup()
        except Exception as error:
            errors.append(error)
    if errors:
        raise ExceptionGroup("Linux input controller cleanup failed", errors)

__all__ = [
    "close",
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
