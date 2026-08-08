"""Tạo và phát event qua virtual keyboard Linux bằng `evdev`.

File path: `src/agent/platform/linux/input_controller/sendinput_kb.py`.
Input: tên phím dạng chuỗi như `a`, `enter`, `leftctrl`; `press` nhận nhiều
chuỗi liên tiếp.
Output: phát event `EV_KEY` qua một `UInput` ảo.
Nguyên lý: khai báo capability `KEY_*`, tạo device bằng helper Linux dùng chung,
chờ Xorg nhận diện rồi giữ device sống trong suốt phiên điều khiển.
"""

import os
import time
from collections.abc import Sequence
from typing import Final

from evdev import ecodes

from agent.platform_protocols import Key
from agent.platform.linux.input_controller.types import UInputDevice
from agent.platform.linux.input_controller.utils import UInputManager


# Ký tự có thể gõ trực tiếp trên layout US/ANSI bằng một phím vật lý.
_DIRECT_CHARS: Final[dict[str, Key]] = {
    "a": "a",
    "b": "b",
    "c": "c",
    "d": "d",
    "e": "e",
    "f": "f",
    "g": "g",
    "h": "h",
    "i": "i",
    "j": "j",
    "k": "k",
    "l": "l",
    "m": "m",
    "n": "n",
    "o": "o",
    "p": "p",
    "q": "q",
    "r": "r",
    "s": "s",
    "t": "t",
    "u": "u",
    "v": "v",
    "w": "w",
    "x": "x",
    "y": "y",
    "z": "z",
    "0": "0",
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
    " ": "space",
    "\n": "enter",
    "\t": "tab",
    "`": "grave",
    "-": "minus",
    "=": "equal",
    "[": "leftbrace",
    "]": "rightbrace",
    "\\": "backslash",
    ";": "semicolon",
    "'": "apostrophe",
    ",": "comma",
    ".": "dot",
    "/": "slash",
}


# Ký tự cần giữ Shift trên layout US/ANSI để app nhận đúng ký tự in ra.
_SHIFT_CHARS: Final[dict[str, Key]] = {
    "A": "a",
    "B": "b",
    "C": "c",
    "D": "d",
    "E": "e",
    "F": "f",
    "G": "g",
    "H": "h",
    "I": "i",
    "J": "j",
    "K": "k",
    "L": "l",
    "M": "m",
    "N": "n",
    "O": "o",
    "P": "p",
    "Q": "q",
    "R": "r",
    "S": "s",
    "T": "t",
    "U": "u",
    "V": "v",
    "W": "w",
    "X": "x",
    "Y": "y",
    "Z": "z",
    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",
    "~": "grave",
    "_": "minus",
    "+": "equal",
    "{": "leftbrace",
    "}": "rightbrace",
    "|": "backslash",
    ":": "semicolon",
    '"': "apostrophe",
    "<": "comma",
    ">": "dot",
    "?": "slash",
}


# Danh sách capability cho virtual keyboard này.
# Mục tiêu: support layout bàn phím phổ biến kiểu ANSI/US 104 phím,
# cộng thêm vài phím mở rộng thường có trên keyboard hiện đại.
#
# Khuyen nghi tim hieu co ban ve linux input system truoc evdev lib
# Tham khảo:
# - evdev docs: https://python-evdev.readthedocs.io/en/latest/tutorial.html#injecting-input
# - Linux input event codes: https://www.kernel.org/doc/html/latest/input/event-codes.html
# - ANSI - ISO layout: https://www.logitech.com/en-us/discover/a/ansi-vs-iso-keyboards

_KEY_CODES: Final[list[int]] = [
    # Letters
    # Phím chữ cái từ A đến Z; hoa/thường do Shift hoặc CapsLock quyết định.
    ecodes.KEY_A,
    ecodes.KEY_B,
    ecodes.KEY_C,
    ecodes.KEY_D,
    ecodes.KEY_E,
    ecodes.KEY_F,
    ecodes.KEY_G,
    ecodes.KEY_H,
    ecodes.KEY_I,
    ecodes.KEY_J,
    ecodes.KEY_K,
    ecodes.KEY_L,
    ecodes.KEY_M,
    ecodes.KEY_N,
    ecodes.KEY_O,
    ecodes.KEY_P,
    ecodes.KEY_Q,
    ecodes.KEY_R,
    ecodes.KEY_S,
    ecodes.KEY_T,
    ecodes.KEY_U,
    ecodes.KEY_V,
    ecodes.KEY_W,
    ecodes.KEY_X,
    ecodes.KEY_Y,
    ecodes.KEY_Z,
    # Number row
    ecodes.KEY_1,
    ecodes.KEY_2,
    ecodes.KEY_3,
    ecodes.KEY_4,
    ecodes.KEY_5,
    ecodes.KEY_6,
    ecodes.KEY_7,
    ecodes.KEY_8,
    ecodes.KEY_9,
    ecodes.KEY_0,
    # Function keys
    # Bao phủ toàn bộ phím chức năng từ F1 đến F12.
    ecodes.KEY_F1,
    ecodes.KEY_F2,
    ecodes.KEY_F3,
    ecodes.KEY_F4,
    ecodes.KEY_F5,
    ecodes.KEY_F6,
    ecodes.KEY_F7,
    ecodes.KEY_F8,
    ecodes.KEY_F9,
    ecodes.KEY_F10,
    ecodes.KEY_F11,
    ecodes.KEY_F12,
    # Top row / editing
    ecodes.KEY_ESC,
    ecodes.KEY_GRAVE,
    ecodes.KEY_MINUS,  # - _
    ecodes.KEY_EQUAL,
    ecodes.KEY_BACKSPACE,
    ecodes.KEY_TAB,
    ecodes.KEY_LEFTBRACE,  # [ {
    ecodes.KEY_RIGHTBRACE,  # ] }
    ecodes.KEY_BACKSLASH,  # \ |
    ecodes.KEY_ENTER,
    # Home row / bottom row
    ecodes.KEY_CAPSLOCK,
    ecodes.KEY_SEMICOLON,  # ; :
    ecodes.KEY_APOSTROPHE,  # ' "
    ecodes.KEY_LEFTSHIFT,
    ecodes.KEY_RIGHTSHIFT,
    ecodes.KEY_COMMA,  # , <
    ecodes.KEY_DOT,  # . >
    ecodes.KEY_SLASH,
    # Modifiers
    ecodes.KEY_LEFTCTRL,
    ecodes.KEY_RIGHTCTRL,
    ecodes.KEY_LEFTALT,
    ecodes.KEY_RIGHTALT,
    ecodes.KEY_LEFTMETA,  # phím Windows / Super trái
    ecodes.KEY_RIGHTMETA,  # phím Windows / Super phải
    ecodes.KEY_SPACE,
    ecodes.KEY_COMPOSE,  # phím Menu/Application (thường mở menu ngữ cảnh / context menu)
    # Navigation
    ecodes.KEY_INSERT,
    ecodes.KEY_DELETE,
    ecodes.KEY_HOME,
    ecodes.KEY_END,
    ecodes.KEY_PAGEUP,
    ecodes.KEY_PAGEDOWN,
    # Arrow keys
    ecodes.KEY_UP,
    ecodes.KEY_DOWN,
    ecodes.KEY_LEFT,
    ecodes.KEY_RIGHT,
    # Locks / misc
    ecodes.KEY_NUMLOCK,
    ecodes.KEY_SCROLLLOCK,
    ecodes.KEY_SYSRQ,  # Print Screen / SysRq (chụp màn hình hoặc chức năng hệ thống đặc biệt)
    ecodes.KEY_PAUSE,  # Pause/Break
    # ISO keyboard: thêm phím `102ND` cạnh Left Shift.
    ecodes.KEY_102ND,  # phím < > | trên layout ISO
    # Numeric keypad - Cac phim ben numpad
    ecodes.KEY_KP0,  # numpad 0
    ecodes.KEY_KP1,  # numpad 1
    ecodes.KEY_KP2,  # numpad 2
    ecodes.KEY_KP3,  # numpad 3
    ecodes.KEY_KP4,  # numpad 4
    ecodes.KEY_KP5,  # numpad 5
    ecodes.KEY_KP6,  # numpad 6
    ecodes.KEY_KP7,  # numpad 7
    ecodes.KEY_KP8,  # numpad 8
    ecodes.KEY_KP9,  # numpad 9
    ecodes.KEY_KPDOT,  # numpad .
    ecodes.KEY_KPPLUS,  # numpad +
    ecodes.KEY_KPMINUS,  # numpad -
    ecodes.KEY_KPASTERISK,  # numpad *
    ecodes.KEY_KPSLASH,  # numpad /
    ecodes.KEY_KPENTER,  # numpad Enter
]


_DEVICE_NAME: Final[str] = f"Sigma Virtual Keyboard {os.getpid()}"
_ui_manager = UInputManager(
    _DEVICE_NAME,
    {
        ecodes.EV_KEY: _KEY_CODES,
        ecodes.EV_REP: [],
    },
)


def _get_ui() -> UInputDevice:
    """Tạo virtual keyboard ở lần sử dụng đầu tiên."""

    return _ui_manager.get_ui()


def keyDown(key: Key) -> None:
    """Nhấn và giữ một phím trên virtual keyboard."""

    ui = _get_ui()
    code = getattr(ecodes, "KEY_" + key.upper())
    # IMPORTANT!: bat buoc phai gui hold event!
    ui.write(ecodes.EV_KEY, code, 1)  # Down
    # ui.write(ecodes.EV_KEY, code, 2)  # Hold
    ui.syn()


def keyUp(key: Key) -> None:
    """Thả một phím đang được giữ trên virtual keyboard."""

    ui = _get_ui()
    code = getattr(ecodes, "KEY_" + key.upper())
    ui.write(ecodes.EV_KEY, code, 0)
    ui.syn()


def press(keys: Key | Sequence[Key]) -> None:
    """Nhấn rồi thả lần lượt một phím hoặc một dãy phím."""

    key_names = (keys,) if isinstance(keys, str) else keys
    for key in key_names:
        keyDown(key)
        keyUp(key)


def write(message: str, interval: float = 0.0) -> None:
    """Gõ chuỗi text theo layout US/ANSI bằng `press` và Shift khi cần."""

    for character in message:
        if character in _DIRECT_CHARS:
            press(_DIRECT_CHARS[character])
            if interval:
                time.sleep(interval)
            continue
        if character in _SHIFT_CHARS:
            keyDown("leftshift")
            press(_SHIFT_CHARS[character])
            keyUp("leftshift")
            if interval:
                time.sleep(interval)
            continue
        raise ValueError(f"Unsupported character: {character!r}")


def supportedKeys() -> tuple[str, ...]:
    """Trả về danh sách tên phím có thể truyền vào `press`, `keyDown`, `keyUp`."""

    names: list[str] = []
    for code in _KEY_CODES:
        for name, mapped_code in ecodes.ecodes.items():
            if mapped_code == code and name.startswith("KEY_"):
                names.append(name.removeprefix("KEY_").lower())
                break
    return tuple(names)


def supportedWriteCharacters() -> str:
    """Trả về các ký tự có thể truyền vào `write` trên layout US/ANSI."""

    return "".join(_DIRECT_CHARS) + "".join(_SHIFT_CHARS)


def close() -> None:
    """Đóng virtual keyboard nếu đã được tạo."""

    _ui_manager.close()


__all__ = [
    "close",
    "keyDown",
    "keyUp",
    "press",
    "supportedKeys",
    "supportedWriteCharacters",
    "write",
]
