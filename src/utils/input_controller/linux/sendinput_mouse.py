"""Gửi mouse event qua virtual device Linux bằng `evdev.UInput`.

UInput device phải được tạo trước và giữ sống trong suốt phiên điều khiển để
Xorg/libinput có thời gian nhận diện. Nếu tạo device, gửi event rồi hủy ngay,
event đầu tiên có thể bị mất vì Xorg chưa attach xong.
"""

import os
import time
from typing import Final, Protocol, cast
import subprocess

from evdev import ecodes
from Xlib.display import Display

from utils.input_controller.linux.types import UInputDevice
from utils.input_controller.linux.utils import UInputManager
from utils.input_controller.types import MouseButton

# Đổi tên nút public sang BTN_* code mà Linux input subsystem sử dụng.
_BUTTON_CODES: Final[dict[MouseButton, int]] = {
    "left": ecodes.BTN_LEFT,
    "right": ecodes.BTN_RIGHT,
    "middle": ecodes.BTN_MIDDLE,
    "forward": ecodes.BTN_FORWARD,
    "back": ecodes.BTN_BACK,
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
_DEVICE_NAME: Final[str] = f"Sigma Virtual Mouse {os.getpid()}"
_ui_manager = UInputManager(
    _DEVICE_NAME,
    {
        ecodes.EV_KEY: list(_BUTTON_CODES.values()),
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
    ui = _ui_manager.get_ui()
    device_name = ui.name
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


def click(button: MouseButton) -> None:
    mouseDown(button)
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


def moveTo(x: int, y: int, steps: int = 1, duration: int | float = 0) -> None:
    """Di chuyen de toa DO (X, Y) tren mang hinh"""

    current_x, current_y = position()
    moveRel(x - current_x, y - current_y, steps, duration)


def moveRel(x: int, y: int, steps: int = 1, duration: int | float = 0) -> None:
    """Di chuyen tuong doi dden toa do (x, y) tren mang hinh tu vi tri hien tai
    x > 0       Qua phia
    x < 0       Qua tri
    y > 0       Xuong duoi
    y < 0       Len tren"""

    curx, cury = position()
    goalx, goaly = curx + x, cury + y
    ui = _get_ui()
    step_delay = duration / steps

    for step_left in range(steps, 0, -1):
        curx, cury = position()
        nextx = int((goalx - curx) / step_left)
        nexty = int((goaly - cury) / step_left)
        ui.write(ecodes.EV_REL, ecodes.REL_X, nextx)
        ui.write(ecodes.EV_REL, ecodes.REL_Y, nexty)
        ui.syn()
        time.sleep(step_delay)


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
