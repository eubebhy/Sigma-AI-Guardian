"""Gửi mouse event qua virtual device Linux bằng `evdev.UInput`.

File path: `src/agent/platform/linux/input_controller/sendinput_mouse.py`.
Input: nút chuột, tọa độ, thời lượng và lượng cuộn theo public API chung.
Output: event điều khiển mouse qua UInput và X11.
Nguyên lý: giữ virtual device sống trong suốt phiên để Xorg/libinput nhận diện.

UInput device phải được tạo trước và giữ sống trong suốt phiên điều khiển để
Xorg/libinput có thời gian nhận diện. Nếu tạo device, gửi event rồi hủy ngay,
event đầu tiên có thể bị mất vì Xorg chưa attach xong.
"""

import logging
import os
import time
from math import ceil
from typing import Final, Protocol, cast
import subprocess

from evdev import ecodes
from Xlib.display import Display

from agent.platform_protocols import MouseButton
from agent.platform.linux.input_controller.types import Capabilities, UInputDevice
from agent.platform.linux.input_controller.utils import UInputManager


logger = logging.getLogger(__name__)

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


_MOVEMENT_INTERVAL: Final[float] = 0.1
_DEVICE_NAME: Final[str] = f"Sigma Virtual Mouse {os.getpid()}"
_CAPABILITIES: Final[Capabilities] = {
    ecodes.EV_KEY: list(dict.fromkeys(_BUTTON_CODES.values())),
    ecodes.EV_REL: [
        ecodes.REL_X,
        ecodes.REL_Y,
        ecodes.REL_WHEEL,
        ecodes.REL_HWHEEL,
    ],
}


class MouseInput:
    """Sở hữu virtual mouse và X11 connection của một input controller Linux."""

    def __init__(self) -> None:
        device_name = f"{_DEVICE_NAME} {id(self)}"
        self.ui_manager = UInputManager(device_name, _CAPABILITIES)
        self.configured_device_name: str | None = None
        self.display: Display | None = None
        self.root: _Root | None = None

    def close(self) -> None:
        errors: list[Exception] = []
        try:
            self.ui_manager.close()
        except Exception as error:
            errors.append(error)
        self.configured_device_name = None
        self.root = None
        if self.display is not None:
            try:
                self.display.close()
            except Exception as error:
                errors.append(error)
            else:
                self.display = None
        if errors:
            raise ExceptionGroup("Linux mouse cleanup failed", errors)

    def get_ui(self) -> UInputDevice:
        ui = self.ui_manager.get_ui()
        if self.configured_device_name != ui.name:
            _configure_mouse(ui.name)
            self.configured_device_name = ui.name
        return ui

    def get_root(self) -> _Root:
        if self.root is not None:
            return self.root
        last_error: Exception | None = None
        for attempt in range(1, 4):
            display: Display | None = None
            try:
                display = Display()
                self.root = cast(_Root, display.screen().root)
                self.display = display
                return self.root
            except Exception as error:
                if display is not None:
                    display.close()
                last_error = error
                logger.debug(
                    "X server connection attempt %s of 3 failed: %s", attempt, error
                )
        raise RuntimeError("Cannot connect to X server") from last_error

    def position(self, take_new: bool = False) -> tuple[int, int]:
        pointer = self.get_root().query_pointer()
        return pointer.root_x, pointer.root_y

    def moveRel(self, x: int | None, y: int | None, duration: float = 0.0) -> None:
        ui = self.get_ui()
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

    def moveTo(self, x: int | None, y: int | None, duration: float = 0.0) -> None:
        current_x, current_y = self.position()
        target_x = current_x if x is None else x
        target_y = current_y if y is None else y
        self.moveRel(target_x - current_x, target_y - current_y, duration)

    def mouseDown(self, button: MouseButton) -> None:
        ui = self.get_ui()
        ui.write(ecodes.EV_KEY, _BUTTON_CODES[button], 1)
        ui.syn()

    def mouseUp(self, button: MouseButton) -> None:
        ui = self.get_ui()
        ui.write(ecodes.EV_KEY, _BUTTON_CODES[button], 0)
        ui.syn()

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: MouseButton = "primary",
    ) -> None:
        if x is not None or y is not None:
            self.moveTo(x, y)
        self.mouseDown(button)
        time.sleep(0.02467)
        self.mouseUp(button)

    def scroll(self, amount: int) -> None:
        ui = self.get_ui()
        ui.write(ecodes.EV_REL, ecodes.REL_WHEEL, amount)
        ui.syn()

    def sideScroll(self, amount: int) -> None:
        ui = self.get_ui()
        ui.write(ecodes.EV_REL, ecodes.REL_HWHEEL, amount)
        ui.syn()


# Rat qyan trong, tat truot con tro tren X11
def _configure_mouse(device_name: str) -> None:
    """Tắt acceleration cho virtual mouse mới."""

    subprocess.run(
        ["xinput", "set-prop", device_name, "libinput Accel Profile Enabled", "0", "1"],
        check=True,
    )
    subprocess.run(
        ["xinput", "set-prop", device_name, "libinput Accel Speed", "0"],
        check=True,
    )


__all__ = ["MouseInput"]
