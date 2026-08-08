"""API điều khiển input độc lập hệ điều hành theo tập con PyAutoGUI.

File path: `src/device_controller/input_controller/__init__.py`.
Input: lời gọi gửi keyboard hoặc mouse với tham số theo PyAutoGUI.
Output: API gửi input qua platform service phù hợp với hệ điều hành đang chạy.
Nguyên lý: facade giữ public API cũ và lấy adapter mặc định từ Agent. Listener nằm
ở `utils.key_listener`.
"""

from collections.abc import Sequence

from agent.platform_protocols import InputControllerOperations, MouseButton
from agent.platform import get_default_platform_services


def _get_operations() -> InputControllerOperations:
    return get_default_platform_services().input_controller


def click(
    x: int | None = None,
    y: int | None = None,
    button: MouseButton = "primary",
) -> None:
    _get_operations().click(x, y, button)


def keyDown(key: str) -> None:
    _get_operations().keyDown(key)


def keyUp(key: str) -> None:
    _get_operations().keyUp(key)


def mouseDown(button: MouseButton) -> None:
    _get_operations().mouseDown(button)


def mouseUp(button: MouseButton) -> None:
    _get_operations().mouseUp(button)


def moveRel(x: int | None, y: int | None, duration: float = 0.0) -> None:
    _get_operations().moveRel(x, y, duration)


def moveTo(x: int | None, y: int | None, duration: float = 0.0) -> None:
    _get_operations().moveTo(x, y, duration)


def position(take_new: bool = False) -> tuple[int, int]:
    return _get_operations().position(take_new)


def press(keys: str | Sequence[str]) -> None:
    _get_operations().press(keys)


def scroll(amount: int) -> None:
    _get_operations().scroll(amount)


def sideScroll(amount: int) -> None:
    _get_operations().sideScroll(amount)


def supportedKeys() -> tuple[str, ...]:
    return _get_operations().supportedKeys()


def supportedWriteCharacters() -> str:
    return _get_operations().supportedWriteCharacters()


def write(message: str, interval: float = 0.0) -> None:
    _get_operations().write(message, interval)


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
