"""Kiểu event dùng chung cho listener Windows và Linux.

File path: `src/utils/key_listener/types.py`.
Input: mã event keyboard/mouse chuẩn hóa từ backend hệ điều hành.
Output: type alias event cho caller của listener.
Nguyên lý: event không phụ thuộc backend để system monitor dùng cùng một contract.
"""

from typing import Literal, TypeAlias

KeyState: TypeAlias = Literal["down", "up", "hold"]
KeyEvent: TypeAlias = tuple[str, KeyState]
MouseState: TypeAlias = Literal["down", "up"]
MouseButtonEvent: TypeAlias = tuple[str, MouseState]
MouseMoveEvent: TypeAlias = tuple[str, int]
MouseEvent: TypeAlias = MouseButtonEvent | MouseMoveEvent

__all__ = [
    "KeyEvent",
    "KeyState",
    "MouseButtonEvent",
    "MouseEvent",
    "MouseMoveEvent",
    "MouseState",
]
