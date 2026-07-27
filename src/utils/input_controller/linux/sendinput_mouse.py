"""Gửi mouse event qua virtual device Linux bằng `evdev.UInput`.

UInput device phải được tạo trước và giữ sống trong suốt phiên điều khiển để
Xorg/libinput có thời gian nhận diện. Nếu tạo device, gửi event rồi hủy ngay,
event đầu tiên có thể bị mất vì Xorg chưa attach xong.
"""

import os
import time
from math import ceil
from typing import Final, Protocol, cast
import subprocess

from evdev import ecodes
from Xlib.display import Display

from utils.input_controller.linux.types import UInputDevice
from utils.input_controller.linux.utils import UInputManager
from utils.input_controller.types import MouseButton

# Đổi tên nút public sang BTN_* code mà Linux input subsystem sử dụng.
_BUTTON_CODES: Final[dict[MouseButton, int]] = {
    "primary": ecodes.BTN_LEFT,
    "secondary": ecodes.BTN_RIGHT,
    "left": ecodes.BTN_LEFT,
    "right": ecodes.BTN_RIGHT,
    "middle": ecodes.BTN_MIDDLE,
    "forward": ecodes.BTN_EXTRA,  # No khong phai BTN_FORWARD
    "back": ecodes.BTN_SIDE,  # Not BTN_BACK
}


class _Pointer(Protocol):
    root_x: int
    root_y: int


class _Root(Protocol):
    def query_pointer(self) -> _Pointer:
        """Trả vị trí con trỏ trên root window."""
        ...


_display: Display | None = None
_root: _Root | None = None
_configured_device_name: str | None = None
_MOVEMENT_INTERVAL: Final[float] = 0.1
_DEVICE_NAME: Final[str] = f"Sigma Virtual Mouse {os.getpid()}"
_ui_manager = UInputManager(
    _DEVICE_NAME,
    {
        ecodes.EV_KEY: list(dict.fromkeys(_BUTTON_CODES.values())),
        ecodes.EV_REL: [
            ecodes.REL_X,
            ecodes.REL_Y,
            ecodes.REL_WHEEL,
            ecodes.REL_HWHEEL,
        ],
    },
)


def _get_ui() -> UInputDevice:
    """Tạo virtual mouse ở lần sử dụng đầu tiên."""

    global _configured_device_name

    ui = _ui_manager.get_ui()
    device_name = ui.name
    if _configured_device_name == device_name:
        return ui

    subprocess.run(
        [
            "xinput",
            "set-prop",
            device_name,
            "libinput Accel Profile Enabled",
            "0",
            "1",
        ],
        check=True,
    )
    subprocess.run(
        [
            "xinput",
            "set-prop",
            device_name,
            "libinput Accel Speed",
            "0",
        ],
        check=True,
    )
    _configured_device_name = device_name
    return ui


def _get_root() -> _Root:
    """Kết nối X server ở lần cần đọc vị trí con trỏ đầu tiên."""
    global _display, _root

    if _root is not None:
        return _root

    last_error: Exception | None = None

    for _ in range(3):
        try:
            _display = Display()
            _root = cast(_Root, _display.screen().root)
            return _root
        except Exception as error:
            last_error = error

    raise RuntimeError("Cannot connect to X server") from last_error


def click(
    x: int | None = None,
    y: int | None = None,
    button: MouseButton = "primary",
) -> None:
    """Click tại tọa độ chỉ định hoặc giữ nguyên vị trí hiện tại."""

    if x is not None or y is not None:
        moveTo(x, y)
    mouseDown(button)
    time.sleep(0.02467)
    mouseUp(button)


def mouseDown(button: MouseButton) -> None:
    code = _BUTTON_CODES[button]
    ui = _get_ui()
    ui.write(ecodes.EV_KEY, code, 1)
    ui.syn()


def mouseUp(button: MouseButton) -> None:
    code = _BUTTON_CODES[button]
    ui = _get_ui()
    ui.write(ecodes.EV_KEY, code, 0)
    ui.syn()


old_position: tuple[int, int] | None = None


def position(take_new: bool = False) -> tuple[int, int]:

    pointer = _get_root().query_pointer()
    newx, newy = pointer.root_x, pointer.root_y

    return newx, newy


def moveTo(x: int | None, y: int | None, duration: float = 0.0) -> None:
    """Di chuyển đến tọa độ tuyệt đối, giữ nguyên trục có giá trị ``None``."""

    current_x, current_y = position()
    target_x = current_x if x is None else x
    target_y = current_y if y is None else y
    moveRel(target_x - current_x, target_y - current_y, duration)


def moveRel(x: int | None, y: int | None, duration: float = 0.0) -> None:
    """Di chuyển theo độ lệch, xem ``None`` là độ lệch bằng không."""

    ui = _get_ui()
    steps = max(1, ceil(duration / _MOVEMENT_INTERVAL))
    remaining_x = 0 if x is None else x
    remaining_y = 0 if y is None else y
    step_duration = duration / steps

    for steps_left in range(steps, 0, -1):
        step_x = int(remaining_x / steps_left)
        step_y = int(remaining_y / steps_left)
        ui.write(ecodes.EV_REL, ecodes.REL_X, step_x)
        ui.write(ecodes.EV_REL, ecodes.REL_Y, step_y)
        ui.syn()
        remaining_x -= step_x
        remaining_y -= step_y
        if step_duration:
            time.sleep(step_duration)


def scroll(amount: int) -> None:
    """Cuộn dọc; số dương cuộn lên, số âm cuộn xuống."""

    ui = _get_ui()
    ui.write(ecodes.EV_REL, ecodes.REL_WHEEL, amount)
    ui.syn()


def sideScroll(amount: int) -> None:
    """Cuộn ngang; số dương sang phải, số âm sang trái."""

    ui = _get_ui()
    ui.write(ecodes.EV_REL, ecodes.REL_HWHEEL, amount)
    ui.syn()


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
