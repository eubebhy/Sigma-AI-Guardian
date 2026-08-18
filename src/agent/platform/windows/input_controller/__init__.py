"""Facade Windows cho gửi sự kiện bàn phím và chuột.

File path: `src/agent/platform/windows/input_controller/__init__.py`.
Input: lời gọi theo contract chung của input controller.
Output: API sender có cùng chữ ký với backend Linux.
Nguyên lý: chỉ re-export các module con; dependency nền tảng được import lazy bên
trong từng API để package vẫn import được trên Linux. Listener nằm tại
`system_monitor.keylogger`.
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
from agent.platform_protocols import MouseButton
from collections.abc import Sequence


class WindowsInput:
    """Resource gửi input Windows với lifecycle thống nhất giữa các platform."""

    def __init__(self) -> None:
        self._closed = False

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Input is closed")

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: MouseButton = "primary",
    ) -> None:
        self._ensure_open()
        click(x, y, button)

    def keyDown(self, key: str) -> None:
        self._ensure_open()
        keyDown(key)

    def keyUp(self, key: str) -> None:
        self._ensure_open()
        keyUp(key)

    def mouseDown(self, button: MouseButton) -> None:
        self._ensure_open()
        mouseDown(button)

    def mouseUp(self, button: MouseButton) -> None:
        self._ensure_open()
        mouseUp(button)

    def moveRel(self, x: int | None, y: int | None, duration: float = 0.0) -> None:
        self._ensure_open()
        moveRel(x, y, duration)

    def moveTo(self, x: int | None, y: int | None, duration: float = 0.0) -> None:
        self._ensure_open()
        moveTo(x, y, duration)

    def position(self, take_new: bool = False) -> tuple[int, int]:
        self._ensure_open()
        return position(take_new)

    def press(self, keys: str | Sequence[str]) -> None:
        self._ensure_open()
        press(keys)

    def scroll(self, amount: int) -> None:
        self._ensure_open()
        scroll(amount)

    def sideScroll(self, amount: int) -> None:
        self._ensure_open()
        sideScroll(amount)

    def supportedKeys(self) -> tuple[str, ...]:
        self._ensure_open()
        return supportedKeys()

    def supportedWriteCharacters(self) -> str:
        self._ensure_open()
        return supportedWriteCharacters()

    def write(self, message: str, interval: float = 0.0) -> None:
        self._ensure_open()
        write(message, interval)

    def close(self) -> None:
        """Kết thúc lifecycle; Windows sender không cache native resource."""
        self._closed = True

    def create(self):
        self._closed = False


__all__: list[str] = []
