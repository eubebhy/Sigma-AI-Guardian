"""Adapter gửi input Windows cho SAG Agent.

File path: `src/agent/platform/windows/input_controller_operations.py`.
Input/Output: cung cấp 14 operation input controller theo contract Agent.
Nguyên lý: adapter chuyển operation sang native sender Windows được lazy import.
"""

from collections.abc import Sequence

from typing import cast

from agent.contracts import InputControllerOperations, MouseButton


class WindowsInputControllerOperations:
    """Chuyển operation Agent sang backend input controller Windows."""

    @staticmethod
    def _backend() -> InputControllerOperations:
        from agent.platform.windows import input_controller

        return cast(InputControllerOperations, input_controller)

    def click(self, x: int | None = None, y: int | None = None,
              button: MouseButton = "primary") -> None:
        self._backend().click(x, y, button)

    def keyDown(self, key: str) -> None:
        self._backend().keyDown(key)

    def keyUp(self, key: str) -> None:
        self._backend().keyUp(key)

    def mouseDown(self, button: MouseButton) -> None:
        self._backend().mouseDown(button)

    def mouseUp(self, button: MouseButton) -> None:
        self._backend().mouseUp(button)

    def moveRel(self, x: int | None, y: int | None,
                duration: float = 0.0) -> None:
        self._backend().moveRel(x, y, duration)

    def moveTo(self, x: int | None, y: int | None,
               duration: float = 0.0) -> None:
        self._backend().moveTo(x, y, duration)

    def position(self, take_new: bool = False) -> tuple[int, int]:
        return self._backend().position(take_new)

    def press(self, keys: str | Sequence[str]) -> None:
        self._backend().press(keys)

    def scroll(self, amount: int) -> None:
        self._backend().scroll(amount)

    def sideScroll(self, amount: int) -> None:
        self._backend().sideScroll(amount)

    def supportedKeys(self) -> tuple[str, ...]:
        return self._backend().supportedKeys()

    def supportedWriteCharacters(self) -> str:
        return self._backend().supportedWriteCharacters()

    def write(self, message: str, interval: float = 0.0) -> None:
        self._backend().write(message, interval)

    def close(self) -> None:
        """Windows sender không giữ resource sau từng operation."""

        return None
