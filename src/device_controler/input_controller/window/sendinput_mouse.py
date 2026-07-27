"""Wrapper tối thiểu cho mouse API của `pydirectinput-rgx` trên Windows.

File path: `src/device_controler/input_controller/window/sendinput_mouse.py`.
Input: nút chuột, tọa độ, thời lượng và lượng cuộn theo public API chung.
Output: gửi mouse event bằng WinAPI SendInput.
Nguyên lý: thư viện đã hỗ trợ di chuyển theo `duration`, vì wrapper chỉ chuyển
tiếp thao tác. `steps` giữ tương thích API nhưng không cần dùng lại.
"""

from __future__ import annotations

import importlib
from typing import Any, cast

from device_controler.input_controller.types import MouseButton


_BUTTON_NAMES = {
    "primary": "left",
    "secondary": "right",
    "back": "x1",
    "forward": "x2",
}


def _input() -> Any:
    """Import dependency Windows tại thời điểm thực sự gửi input."""

    return cast(Any, importlib.import_module("pydirectinput"))


def _button(button: MouseButton) -> str:
    """Đổi hai tên button chung sang tên của pydirectinput-rgx."""

    return _BUTTON_NAMES.get(button, button)


def click(
    x: int | None = None,
    y: int | None = None,
    button: MouseButton = "primary",
) -> None:
    """Click tại tọa độ chỉ định hoặc vị trí hiện tại."""

    _input().click(x=x, y=y, button=_button(button), _pause=False)


def mouseDown(button: MouseButton) -> None:
    """Nhấn và giữ một nút chuột."""

    _input().mouseDown(button=_button(button), _pause=False)


def mouseUp(button: MouseButton) -> None:
    """Thả một nút chuột."""

    _input().mouseUp(button=_button(button), _pause=False)


def position(take_new: bool = False) -> tuple[int, int]:
    """Trả vị trí con trỏ hiện tại."""

    del take_new
    return _input().position()


def moveTo(x: int | None, y: int | None, duration: float = 0.0) -> None:
    """Di chuyển tới tọa độ tuyệt đối."""

    _input().moveTo(x, y, duration=duration, _pause=False)


def moveRel(x: int | None, y: int | None, duration: float = 0.0) -> None:
    """Di chuyển theo độ lệch."""

    _input().moveRel(x, y, duration=duration, _pause=False)


def scroll(amount: int) -> None:
    """Cuộn dọc; số dương cuộn lên."""

    _input().scroll(amount, _pause=False)


def sideScroll(amount: int) -> None:
    """Cuộn ngang; số dương cuộn sang phải."""

    _input().hscroll(amount, _pause=False)


__all__ = [
    "click",
    "mouseDown",
    "mouseUp",
    "moveRel",
    "moveTo",
    "position",
    "scroll",
    "sideScroll",
]
