"""Adapter gửi input Linux cho SAG Agent.

File path: `src/agent/platform/linux/input_controller_operations.py`.
Input/Output: cung cấp 14 operation input controller qua backend Linux hiện có.
Nguyên lý: adapter giữ API chung; UInput/X11 và lifecycle nằm sau boundary platform.
"""

from collections.abc import Sequence
import threading
from typing import cast

from agent.platform_protocols import InputControllerOperations, MouseButton


_lock = threading.RLock()
_active_operations = 0


class LinuxInputControllerOperations:
    """Chuyển operation Agent sang backend input controller Linux."""

    def __init__(self) -> None:
        self._active = False

    def _backend(self) -> InputControllerOperations:
        global _active_operations

        with _lock:
            if not self._active:
                _active_operations += 1
                self._active = True
        from agent.platform.linux import input_controller

        return cast(InputControllerOperations, input_controller)

    def click(self, x: int | None = None, y: int | None = None,
              button: MouseButton = "primary") -> None:
        with _lock:
            self._backend().click(x, y, button)

    def keyDown(self, key: str) -> None:
        with _lock:
            self._backend().keyDown(key)

    def keyUp(self, key: str) -> None:
        with _lock:
            self._backend().keyUp(key)

    def mouseDown(self, button: MouseButton) -> None:
        with _lock:
            self._backend().mouseDown(button)

    def mouseUp(self, button: MouseButton) -> None:
        with _lock:
            self._backend().mouseUp(button)

    def moveRel(self, x: int | None, y: int | None,
                duration: float = 0.0) -> None:
        with _lock:
            self._backend().moveRel(x, y, duration)

    def moveTo(self, x: int | None, y: int | None,
               duration: float = 0.0) -> None:
        with _lock:
            self._backend().moveTo(x, y, duration)

    def position(self, take_new: bool = False) -> tuple[int, int]:
        with _lock:
            return self._backend().position(take_new)

    def press(self, keys: str | Sequence[str]) -> None:
        with _lock:
            self._backend().press(keys)

    def scroll(self, amount: int) -> None:
        with _lock:
            self._backend().scroll(amount)

    def sideScroll(self, amount: int) -> None:
        with _lock:
            self._backend().sideScroll(amount)

    def supportedKeys(self) -> tuple[str, ...]:
        with _lock:
            return self._backend().supportedKeys()

    def supportedWriteCharacters(self) -> str:
        with _lock:
            return self._backend().supportedWriteCharacters()

    def write(self, message: str, interval: float = 0.0) -> None:
        with _lock:
            self._backend().write(message, interval)

    def close(self) -> None:
        """Đóng resource native được Linux input controller cache."""

        global _active_operations

        from agent.platform.linux import input_controller

        with _lock:
            if not self._active:
                return
            _active_operations -= 1
            self._active = False
            if _active_operations == 0:
                input_controller.close()
