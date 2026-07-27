"""Kiểu chung cho API điều khiển input Linux và Windows.

File path: `src/device_controler/input_controller/types.py`.
Input: tên phím, nút chuột và tọa độ theo tập con tương thích PyAutoGUI.
Output: `InputBackend` để facade điều khiển và `__init__.py` kiểm tra tĩnh.
Nguyên lý: backend nhận chuỗi phím, chuẩn hóa nút chuột rồi phát event nền tảng.
"""

from collections.abc import Sequence
from typing import Literal, Protocol, TypeAlias

Key: TypeAlias = str
Keys: TypeAlias = Key
MouseButton: TypeAlias = Literal[
    "primary",
    "secondary",
    "left",
    "right",
    "middle",
    "forward",
    "back",
]


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
    "Keys",
    "MouseButton",
]
