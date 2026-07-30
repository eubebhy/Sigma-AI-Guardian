"""Type nội bộ dùng chung cho Linux input controller.

File path: `src/agent/platform/linux/input_controller/types.py`.
Input/Output: mô tả capability, UInput object và kết quả query XInput2.
Module này chỉ khai báo contract; logic lifecycle nằm trong `linux/utils.py`.
"""

from collections.abc import Sequence
from typing import Protocol, TypeAlias

Capabilities: TypeAlias = dict[int, Sequence[int]]


class UInputDevice(Protocol):
    """Phần `evdev.UInput` mà input sender sử dụng."""

    fd: int
    name: str

    def write(self, event_type: int, code: int, value: int) -> None:
        """Ghi một input event vào virtual device."""
        ...

    def syn(self) -> None:
        """Kết thúc nhóm input event hiện tại."""
        ...

    def close(self) -> None:
        """Hủy virtual device và đóng file descriptor."""
        ...


class XInputDevice(Protocol):
    name: str


class XInputReply(Protocol):
    devices: Sequence[XInputDevice]


class XInputDisplay(Protocol):
    def xinput_query_device(self, deviceid: int) -> XInputReply:
        """Trả danh sách input device mà Xorg đã nhận diện."""
        ...

    def close(self) -> None:
        """Đóng kết nối X11."""
        ...


__all__ = [
    "Capabilities",
    "UInputDevice",
    "XInputDevice",
    "XInputDisplay",
    "XInputReply",
]
