#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# input_blocker.py
"""Backend Linux để chặn input bằng evdev grab.

File path: `src/utils/input_blocker/linux.py`
Input: `block()` và `unblock()` không nhận tham số.
Output: các `/dev/input/event*` hiện có bị grab độc quyền hoặc được release.

Nguyên lý hoạt động: `block()` mở từng thiết bị input và giữ file descriptor trong
`_grabbed_devices`; Linux chỉ giữ trạng thái grab khi descriptor còn mở. `unblock()`
ungrab, đóng descriptor và xoá khỏi registry nội bộ.

Yêu cầu: process cần quyền đọc/grab các thiết bị trong `/dev/input`.
"""

from evdev import InputDevice, list_devices
from pathlib import Path

_grabbed_devices: dict[str, InputDevice] = {}


def block() -> None:
    """Grab toàn bộ thiết bị `/dev/input/event*` hiện có."""

    global _grabbed_devices

    for dev_path in list_devices():
        path = str(Path(dev_path))  # normalize path key

        if path in _grabbed_devices:  # already grabbed
            continue

        dev: InputDevice | None = None
        try:
            dev = InputDevice(path)  # open device
            dev.grab()  # take exclusive input
            _grabbed_devices[path] = dev  # keep handle for release
        except Exception:
            try:
                if dev is not None:
                    dev.close()  # cleanup half-open device
            except Exception:
                pass


def unblock() -> None:
    """Release tất cả thiết bị đã bị `block()` grab trong process này."""

    global _grabbed_devices

    for path, dev in list(_grabbed_devices.items()):
        try:
            dev.ungrab()  # release input
        except Exception:
            pass

        try:
            dev.close()  # close handle
        except Exception:
            pass

        _grabbed_devices.pop(path, None)  # forget released device
