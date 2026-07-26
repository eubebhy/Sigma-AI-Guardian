"""Hợp đồng API chung cho backend input Linux và Windows.

File path: `src/utils/input_controller/types.py`.
Input: tên phím, nút chuột và tọa độ theo tập con tương thích PyAutoGUI.
Output: `InputBackend` để facade hệ điều hành và `__init__.py` kiểm tra tĩnh.
Nguyên lý: backend nhận chuỗi phím, chuẩn hóa nút chuột rồi phát event nền tảng.
"""

from collections.abc import Sequence
from typing import Literal, Protocol, TypeAlias

Key: TypeAlias = str
Keys: TypeAlias = Key
KeyState: TypeAlias = Literal["down", "up", "hold"]
KeyEvent: TypeAlias = tuple[str, KeyState]
MouseButton: TypeAlias = Literal[
    "primary",
    "secondary",
    "left",
    "right",
    "middle",
    "forward",
    "back",
]
MouseState: TypeAlias = Literal["down", "up"]
MouseButtonEvent: TypeAlias = tuple[str, MouseState]
MouseMoveEvent: TypeAlias = tuple[str, int]
MouseEvent: TypeAlias = MouseButtonEvent | MouseMoveEvent


class InputBackend(Protocol):
    """Các thao tác gửi input mà mọi backend phải cung cấp."""

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: MouseButton = "primary",
    ) -> None:
        """Click tại tọa độ chỉ định hoặc vị trí hiện tại."""
        ...

    def moveTo(
        self,
        x: int | None,
        y: int | None,
        duration: float = 0.0,
    ) -> None:
        """Di chuyển đến tọa độ tuyệt đối."""
        ...

    def moveRel(
        self,
        x: int | None,
        y: int | None,
        duration: float = 0.0,
    ) -> None:
        """Di chuyển theo độ lệch."""
        ...

    def write(self, message: str, interval: float = 0.0) -> None:
        """Gõ chuỗi ký tự với khoảng cách giữa các ký tự."""
        ...

    def press(self, keys: Key | Sequence[Key]) -> None:
        """Nhấn rồi thả một hoặc nhiều phím."""
        ...

    def keyDown(self, key: Key) -> None:
        """Nhấn và giữ một phím."""
        ...

    def keyUp(self, key: Key) -> None:
        """Thả một phím."""
        ...


__all__ = [
    "InputBackend",
    "Key",
    "KeyEvent",
    "KeyState",
    "Keys",
    "MouseButton",
    "MouseButtonEvent",
    "MouseEvent",
    "MouseMoveEvent",
    "MouseState",
]
