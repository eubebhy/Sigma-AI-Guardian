"""Backend điều khiển input Linux theo tập con API PyAutoGUI.

File path: `src/agent/platform/linux/input_controller/__init__.py`.
Input: lời gọi sender chuẩn hóa từ facade package cha.
Output: API sender dùng virtual evdev/UInput.
Nguyên lý: module chỉ re-export sender; listener nằm tại `utils.key_listener`.
"""

from agent.platform.linux.input_controller.sendinput_kb import (
    KeyboardInput,
    supportedKeys,
    supportedWriteCharacters,
)
from agent.platform.linux.input_controller.sendinput_mouse import (
    MouseInput,
)

from agent.platform_protocols import MouseButton
from collections.abc import Sequence


class LinuxInput:
    """Resource gửi input Linux và sở hữu lifecycle backend native."""

    def __init__(self) -> None:
        self._closed = True
        self.create()

    def _get_keyboard(self) -> KeyboardInput:
        if self._closed or self._keyboard is None:
            raise RuntimeError("Input is closed")
        return self._keyboard

    def _get_mouse(self) -> MouseInput:
        if self._closed or self._mouse is None:
            raise RuntimeError("Input is closed")
        return self._mouse

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: MouseButton = "primary",
    ) -> None:
        self._get_mouse().click(x, y, button)

    def keyDown(self, key: str) -> None:
        self._get_keyboard().keyDown(key)

    def keyUp(self, key: str) -> None:
        self._get_keyboard().keyUp(key)

    def mouseDown(self, button: MouseButton) -> None:
        self._get_mouse().mouseDown(button)

    def mouseUp(self, button: MouseButton) -> None:
        self._get_mouse().mouseUp(button)

    def moveRel(self, x: int | None, y: int | None, duration: float = 0.0) -> None:
        self._get_mouse().moveRel(x, y, duration)

    def moveTo(self, x: int | None, y: int | None, duration: float = 0.0) -> None:
        self._get_mouse().moveTo(x, y, duration)

    def position(self, take_new: bool = False) -> tuple[int, int]:
        return self._get_mouse().position(take_new)

    def press(self, keys: str | Sequence[str]) -> None:
        self._get_keyboard().press(keys)

    def scroll(self, amount: int) -> None:
        self._get_mouse().scroll(amount)

    def sideScroll(self, amount: int) -> None:
        self._get_mouse().sideScroll(amount)

    def supportedKeys(self) -> tuple[str, ...]:
        self._get_keyboard()
        return supportedKeys()

    def supportedWriteCharacters(self) -> str:
        self._get_keyboard()
        return supportedWriteCharacters()

    def write(self, message: str, interval: float = 0.0) -> None:
        self._get_keyboard().write(message, interval)

    def close(self) -> None:
        """Đóng UInput và X11 resource; object không dùng lại sau khi đóng."""

        if self._closed:
            return

        errors: list[Exception] = []
        resources = (("_keyboard", self._keyboard), ("_mouse", self._mouse))

        for attribute, resource in resources:
            if resource is None:
                continue
            try:
                resource.close()

            except Exception as error:
                errors.append(error)

            else:
                setattr(self, attribute, None)

        if self._keyboard is None and self._mouse is None:
            self._closed = True

        if errors:
            raise ExceptionGroup("Linux input cleanup failed", errors)

    def create(self):

        self._closed = False
        self._keyboard: KeyboardInput | None = KeyboardInput()
        self._mouse: MouseInput | None = MouseInput()


__all__: list[str] = []
