"""Tạo và quản lý lifecycle của virtual input device Linux.

File path: `src/agent/platform/linux/input_controller/utils.py`.
Input: tên gốc và capability cho một UInput device.
Output: `UInputManager` tái sử dụng device khỏe, đóng và tạo lại device chết.
Nguyên lý: health được cache 5 giây; mỗi lần tạo lại dùng generation mới để
XInput2 không nhầm device mới với device cũ đang được Xorg loại bỏ.
"""

import time
from typing import Final, cast

from evdev import UInput
from Xlib.display import Display
from Xlib.ext import xinput

from agent.platform.linux.input_controller.types import (
    Capabilities,
    UInputDevice,
    XInputDisplay,
)

_XINPUT_READY_TIMEOUT: Final[float] = 2.0
_XINPUT_POLL_INTERVAL: Final[float] = 0.067
_UI_HEALTH_CACHE_SECONDS: Final[float] = 5.0


def _wait_for_xinput_device(name: str) -> None:
    """Poll XInput2 tới khi Xorg nhìn thấy device hoặc hết timeout."""
    # Key noi den x server
    display = cast(XInputDisplay, Display())

    # Tinh thoi diem timeout
    deadline = time.monotonic() + _XINPUT_READY_TIMEOUT

    try:
        while time.monotonic() < deadline:
            # Lay danh sach cac device
            reply = display.xinput_query_device(xinput.AllDevices)

            if any(device.name == name for device in reply.devices):
                return

            time.sleep(_XINPUT_POLL_INTERVAL)

    finally:
        # Luôn đóng kết nối tới X server, kể cả khi có exception.
        display.close()

    raise RuntimeError(f"Xorg did not attach input device: {name}")


def create_ui(name: str, capabilities: Capabilities) -> UInputDevice:
    """Tạo UInput device, chờ Xorg attach và cleanup nếu khởi tạo lỗi."""

    ui = cast(UInputDevice, UInput(capabilities, name=name))
    try:
        _wait_for_xinput_device(name)
    except Exception:
        ui.close()
        raise
    return ui


def ui_alive(ui: UInputDevice) -> bool:
    """Trả về `True` khi fd còn mở và Xorg vẫn nhìn thấy device."""
    # Kiem tra xem UI device con song khong?
    if ui.fd < 0:
        return False

    # Thu gui event sync va check X server attach
    try:
        ui.syn()
        _wait_for_xinput_device(ui.name)
    except Exception:
        return False

    return True


class UInputManager:
    """Giữ, kiểm tra và tạo lại một virtual input device."""

    def __init__(self, name: str, capabilities: Capabilities) -> None:
        self._name = name
        self._capabilities = capabilities
        self._ui: UInputDevice | None = None
        self._generation = 0  # The he \ so lan manager tao UI
        self._last_check = 0.0

    def get_ui(self) -> UInputDevice:
        """Trả device cache hoặc đóng và tạo generation mới khi device chết."""

        now = time.monotonic()
        if self._ui is not None and now - self._last_check < _UI_HEALTH_CACHE_SECONDS:
            return self._ui

        if self._ui is not None and ui_alive(self._ui):
            self._last_check = now
            return self._ui

        if self._ui is not None:
            self._ui.close()

        # Tên mới ngăn readiness nhận nhầm device cũ chưa biến mất khỏi XInput2.
        self._generation += 1
        device_name = f"{self._name}-{self._generation}"

        self._ui = create_ui(device_name, self._capabilities)
        self._last_check = now
        return self._ui

    def close(self) -> None:
        """Đóng device hiện tại và xóa cache của manager."""

        if self._ui is not None:
            self._ui.close()
            self._ui = None
        self._last_check = 0.0


__all__ = ["UInputManager", "create_ui", "ui_alive"]
