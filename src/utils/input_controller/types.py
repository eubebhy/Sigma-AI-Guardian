"""Khai báo kiểu dữ liệu dùng chung cho input controller.

File path: `src/utils/input_controller/types.py`
Input: các module backend Linux/Windows import type alias từ file này.
Output: type alias ổn định cho API public của `input_controller`.
Nguyên lý: chỉ đặt những kiểu mô tả hợp đồng chung giữa các backend ở đây;
kiểu phụ thuộc evdev, Xlib hoặc Win32 phải nằm trong module riêng của từng hệ điều hành.
"""

from typing import Literal, TypeAlias

# Keyboard
# Tên phím vật lý app hỗ trợ gửi, ví dụ: "a", "enter", "leftctrl".
Keys: TypeAlias = Literal[
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "g",
    "h",
    "i",
    "j",
    "k",
    "l",
    "m",
    "n",
    "o",
    "p",
    "q",
    "r",
    "s",
    "t",
    "u",
    "v",
    "w",
    "x",
    "y",
    "z",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "f8",
    "f9",
    "f10",
    "f11",
    "f12",
    "esc",
    "grave",
    "minus",
    "equal",
    "backspace",
    "tab",
    "leftbrace",
    "rightbrace",
    "backslash",
    "enter",
    "capslock",
    "semicolon",
    "apostrophe",
    "leftshift",
    "rightshift",
    "comma",
    "dot",
    "slash",
    "leftctrl",
    "rightctrl",
    "leftalt",
    "rightalt",
    "leftmeta",
    "rightmeta",
    "space",
    "compose",
    "insert",
    "delete",
    "home",
    "end",
    "pageup",
    "pagedown",
    "up",
    "down",
    "left",
    "right",
    "numlock",
    "scrolllock",
    "sysrq",
    "pause",
    "102nd",
    "kp0",
    "kp1",
    "kp2",
    "kp3",
    "kp4",
    "kp5",
    "kp6",
    "kp7",
    "kp8",
    "kp9",
    "kpdot",
    "kpplus",
    "kpminus",
    "kpasterisk",
    "kpslash",
    "kpenter",
]
# Trạng thái phím khi listen, ví dụ: "down" khi nhấn, "up" khi thả.
KeyState: TypeAlias = Literal["down", "up", "hold"]
# Event bàn phím khi listen, ví dụ: ("KEY_A", "down").
KeyEvent: TypeAlias = tuple[str, KeyState]

# Mouse
# Tên nút chuột public để gửi input, ví dụ: "left" hoặc "right".
MouseButton: TypeAlias = Literal["left", "right", "middle", "forward", "back"]
# Trạng thái nút chuột khi listen, ví dụ: "down" hoặc "up".
MouseState: TypeAlias = Literal["down", "up"]
# Event nút chuột khi listen, ví dụ: ("BTN_LEFT", "down").
MouseButtonEvent: TypeAlias = tuple[str, MouseState]
# Event di chuyển/cuộn khi listen, ví dụ: ("REL_X", 12) hoặc ("REL_WHEEL", -1).
MouseMoveEvent: TypeAlias = tuple[str, int]
# Event chuột tổng quát khi listen: nút chuột hoặc di chuyển/cuộn.
MouseEvent: TypeAlias = MouseButtonEvent | MouseMoveEvent

# Cursor
# Tọa độ con trỏ tuyệt đối trên màn hình, ví dụ: (640, 360).
Position: TypeAlias = tuple[int, int]
