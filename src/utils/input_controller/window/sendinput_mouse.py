"""Gửi input chuột Windows qua `pydirectinput-rgx`.

File path: `src/utils/input_controller/window/sendinput_mouse.py`
Input: nút chuột chung, tọa độ, số bước, thời lượng và lượng cuộn.
Output: phát event nút chuột, cuộn hoặc di chuyển tuyệt đối trên Windows.
Nguyên lý: import dependency ở lần gọi hàm; mọi bước di chuyển dùng tọa độ
tuyệt đối nội suy từ điểm đầu để tránh mouse acceleration của Windows.
"""

from __future__ import annotations

import importlib
from typing import Final, Protocol, cast

from utils.input_controller.types import MouseButton


class _PyDirectInput(Protocol):
    """Phần API pydirectinput cần cho mouse sender."""

    def click(self, *, button: str, _pause: bool = True) -> None: ...

    def mouseDown(self, *, button: str, _pause: bool = True) -> None: ...

    def mouseUp(self, *, button: str, _pause: bool = True) -> None: ...

    def position(self) -> tuple[int, int]: ...

    def moveTo(
        self,
        x: int,
        y: int,
        *,
        duration: float = 0,
        _pause: bool = True,
    ) -> None: ...

    def scroll(self, clicks: int, *, _pause: bool = True) -> None: ...

    def hscroll(self, clicks: int, *, _pause: bool = True) -> None: ...


_BUTTON_MAP: Final[dict[MouseButton, str]] = {
    "left": "left",
    "right": "right",
    "middle": "middle",
    "forward": "x2",
    "back": "x1",
}


def click(button: MouseButton) -> None:
    """Nhấn rồi thả một nút chuột."""

    mapped_button = _BUTTON_MAP.get(button)
    if mapped_button is None:
        raise ValueError(f"Unsupported mouse button: {button!r}")
    dependency = cast(
        _PyDirectInput,
        importlib.import_module("pydirectinput"),
    )
    dependency.click(button=mapped_button, _pause=False)


def mouseDown(button: MouseButton) -> None:
    """Nhấn và giữ một nút chuột."""

    mapped_button = _BUTTON_MAP.get(button)
    if mapped_button is None:
        raise ValueError(f"Unsupported mouse button: {button!r}")
    dependency = cast(
        _PyDirectInput,
        importlib.import_module("pydirectinput"),
    )
    dependency.mouseDown(button=mapped_button, _pause=False)


def mouseUp(button: MouseButton) -> None:
    """Thả một nút chuột."""

    mapped_button = _BUTTON_MAP.get(button)
    if mapped_button is None:
        raise ValueError(f"Unsupported mouse button: {button!r}")
    dependency = cast(
        _PyDirectInput,
        importlib.import_module("pydirectinput"),
    )
    dependency.mouseUp(button=mapped_button, _pause=False)


def position(take_new: bool = False) -> tuple[int, int]:
    """Trả vị trí con trỏ hiện tại; `take_new` giữ tương thích với Linux."""

    del take_new
    dependency = cast(
        _PyDirectInput,
        importlib.import_module("pydirectinput"),
    )
    return dependency.position()


def _move(
    x: int,
    y: int,
    steps: int,
    duration: int | float,
    *,
    relative: bool,
) -> None:
    """Nội suy và gửi đúng `steps` điểm bằng chuyển động tuyệt đối."""

    if steps < 1:
        raise ValueError("steps must be at least 1")
    if duration < 0:
        raise ValueError("duration must be non-negative")

    dependency = cast(
        _PyDirectInput,
        importlib.import_module("pydirectinput"),
    )
    start_x, start_y = dependency.position()
    target_x = start_x + x if relative else x
    target_y = start_y + y if relative else y
    delta_x, delta_y = target_x - start_x, target_y - start_y
    step_duration = duration / steps

    for step in range(1, steps + 1):
        dependency.moveTo(
            round(start_x + delta_x * step / steps),
            round(start_y + delta_y * step / steps),
            duration=step_duration,
            _pause=False,
        )


def moveTo(x: int, y: int, steps: int = 1, duration: int | float = 0) -> None:
    """Di chuyển đến tọa độ tuyệt đối qua số bước yêu cầu."""

    _move(x, y, steps, duration, relative=False)


def moveRel(x: int, y: int, steps: int = 1, duration: int | float = 0) -> None:
    """Di chuyển theo độ lệch bằng các điểm tuyệt đối để tránh acceleration."""

    _move(x, y, steps, duration, relative=True)


def scroll(amount: int) -> None:
    """Cuộn dọc; số dương cuộn lên, số âm cuộn xuống."""

    dependency = cast(
        _PyDirectInput,
        importlib.import_module("pydirectinput"),
    )
    dependency.scroll(amount, _pause=False)


def sideScroll(amount: int) -> None:
    """Cuộn ngang; số dương sang phải, số âm sang trái."""

    dependency = cast(
        _PyDirectInput,
        importlib.import_module("pydirectinput"),
    )
    dependency.hscroll(amount, _pause=False)


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
