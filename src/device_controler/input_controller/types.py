"""Kiểu chung cho API điều khiển input Linux và Windows.

File path: `src/device_controler/input_controller/types.py`.
Input: tên phím, nút chuột và tọa độ theo tập con tương thích PyAutoGUI.
Output: `InputBackend` để facade điều khiển và `__init__.py` kiểm tra tĩnh.
Nguyên lý: backend nhận chuỗi phím, chuẩn hóa nút chuột rồi phát event nền tảng.
"""

from agent.contracts import InputControllerOperations, Key, MouseButton

Keys = Key
InputBackend = InputControllerOperations


__all__ = [
    "InputBackend",
    "Key",
    "Keys",
    "MouseButton",
]
