#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# input_blocker.py
"""Backend Linux để chặn input bằng evdev grab.

File path: `src/agent/platform/linux/input_blocker_backend.py`.
Input: `block()` và `unblock()` không nhận tham số.
Output: `block()`/`unblock()` trả `None` khi hoàn tất; lỗi grab/release được raise.

Nguyên lý hoạt động: `block()` mở từng thiết bị input và giữ file descriptor trong
`_grabbed_devices`; Linux chỉ giữ trạng thái grab khi descriptor còn mở. `block()`
rollback mọi descriptor đã mở nếu một grab lỗi. `unblock()` luôn thử ungrab và đóng
mọi descriptor trước khi báo các lỗi release bằng `ExceptionGroup`.

Yêu cầu: process cần quyền đọc/grab các thiết bị trong `/dev/input`.
"""

from evdev import InputDevice, list_devices
from pathlib import Path

_grabbed_devices: dict[str, InputDevice] = {}


def block() -> None:
    """Grab toàn bộ thiết bị `/dev/input/event*` hiện có."""

    global _grabbed_devices

    try:
        for dev_path in list_devices():
            path = str(Path(dev_path))
            if path in _grabbed_devices:
                continue
            dev = InputDevice(path)
            _grabbed_devices[path] = dev
            dev.grab()
    except Exception as error:
        cleanup_errors = _release_grabbed_devices()
        if cleanup_errors:
            raise ExceptionGroup(
                "Input blocking failed and rollback was incomplete",
                [error, *cleanup_errors],
            )
        raise


def _release_grabbed_devices() -> list[Exception]:
    """Thử ungrab và đóng mọi descriptor, rồi trả toàn bộ lỗi gặp phải."""

    errors: list[Exception] = []
    for path, dev in list(_grabbed_devices.items()):
        try:
            dev.ungrab()
        except Exception as error:
            errors.append(error)
        try:
            dev.close()
        except Exception as error:
            errors.append(error)
            continue
        _grabbed_devices.pop(path, None)
    return errors


def unblock() -> None:
    """Release tất cả thiết bị đã bị `block()` grab trong process này."""

    errors = _release_grabbed_devices()
    if errors:
        raise ExceptionGroup("Input unblock failed", errors)
