"""Gửi input bàn phím Windows qua `pydirectinput-rgx`.

File path: `src/utils/input_controller/window/sendinput_kb.py`
Input: tên phím chung từ `Keys` hoặc chuỗi ký tự theo layout US/ANSI.
Output: phát event nhấn/thả phím; helper trả các phím và ký tự được hỗ trợ.
Nguyên lý: ánh xạ tường minh tên phím chung sang pydirectinput, import dependency
ở lần gọi hàm để module vẫn import được trên hệ điều hành khác Windows.
"""

from __future__ import annotations

import importlib
import time
from typing import Final, Protocol, cast

from utils.input_controller.types import Keys


class _PyDirectInput(Protocol):
    """Phần API pydirectinput cần cho keyboard sender."""

    def keyDown(self, key: str, *, _pause: bool = True) -> bool: ...

    def keyUp(self, key: str, *, _pause: bool = True) -> bool: ...


_KEY_MAP: Final[dict[Keys, str]] = {
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
    "f1": "f1",
    "f2": "f2",
    "f3": "f3",
    "f4": "f4",
    "f5": "f5",
    "f6": "f6",
    "f7": "f7",
    "f8": "f8",
    "f9": "f9",
    "f10": "f10",
    "f11": "f11",
    "f12": "f12",
    "esc": "esc",
    "grave": "`",
    "minus": "-",
    "equal": "=",
    "backspace": "backspace",
    "tab": "tab",
    "leftbrace": "[",
    "rightbrace": "]",
    "backslash": "\\",
    "enter": "enter",
    "capslock": "capslock",
    "semicolon": ";",
    "apostrophe": "'",
    "leftshift": "shiftleft",
    "rightshift": "shiftright",
    "comma": ",",
    "dot": ".",
    "slash": "/",
    "leftctrl": "ctrlleft",
    "rightctrl": "ctrlright",
    "leftalt": "altleft",
    "rightalt": "altright",
    "leftmeta": "winleft",
    "rightmeta": "winright",
    "space": "space",
    "compose": "apps",
    "insert": "insert",
    "delete": "delete",
    "home": "home",
    "end": "end",
    "pageup": "pageup",
    "pagedown": "pagedown",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "numlock": "numlock",
    "scrolllock": "scrolllock",
    "sysrq": "printscreen",
    "pause": "pause",
    "kp0": "num0",
    "kp1": "num1",
    "kp2": "num2",
    "kp3": "num3",
    "kp4": "num4",
    "kp5": "num5",
    "kp6": "num6",
    "kp7": "num7",
    "kp8": "num8",
    "kp9": "num9",
    "kpdot": "decimal",
    "kpplus": "add",
    "kpminus": "subtract",
    "kpasterisk": "multiply",
    "kpslash": "divide",
    "kpenter": "numpadenter",
}

_DIRECT_CHARS: Final[dict[str, Keys]] = {
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

_SHIFT_CHARS: Final[dict[str, Keys]] = {
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


def keyDown(key: Keys) -> None:
    """Nhấn và giữ một phím; báo lỗi nếu Windows không gửi được event."""

    mapped_key = _KEY_MAP.get(key)
    if mapped_key is None:
        raise ValueError(f"Unsupported key: {key!r}")
    dependency = cast(
        _PyDirectInput,
        importlib.import_module("pydirectinput"),
    )
    if not dependency.keyDown(mapped_key, _pause=False):
        raise ValueError(f"Could not press key down: {key!r}")


def keyUp(key: Keys) -> None:
    """Thả một phím; báo lỗi nếu Windows không gửi được event."""

    mapped_key = _KEY_MAP.get(key)
    if mapped_key is None:
        raise ValueError(f"Unsupported key: {key!r}")
    dependency = cast(
        _PyDirectInput,
        importlib.import_module("pydirectinput"),
    )
    if not dependency.keyUp(mapped_key, _pause=False):
        raise ValueError(f"Could not release key: {key!r}")


def press(*keys: Keys, delay: float = 0.067) -> None:
    """Nhấn rồi thả lần lượt các phím, có delay giữa từng event."""

    for key in keys:
        keyDown(key)
        if delay:
            time.sleep(delay)
        keyUp(key)
        if delay:
            time.sleep(delay)


def write(text: str, delay: float = 0.067) -> None:
    """Gõ chuỗi theo layout US/ANSI và giữ Shift khi ký tự yêu cầu."""

    for character in text:
        if character in _DIRECT_CHARS:
            press(_DIRECT_CHARS[character], delay=delay)
            continue
        if character in _SHIFT_CHARS:
            keyDown("leftshift")
            try:
                if delay:
                    time.sleep(delay)
                press(_SHIFT_CHARS[character], delay=delay)
            finally:
                keyUp("leftshift")
                if delay:
                    time.sleep(delay)
            continue
        raise ValueError(f"Unsupported character: {character!r}")


def supportedKeys() -> tuple[str, ...]:
    """Trả về tên phím public thực sự được ánh xạ trên Windows."""

    return tuple(_KEY_MAP)


def supportedWriteCharacters() -> str:
    """Trả về các ký tự `write` chấp nhận trên layout US/ANSI."""

    return "".join(_DIRECT_CHARS) + "".join(_SHIFT_CHARS)


__all__ = [
    "keyDown",
    "keyUp",
    "press",
    "supportedKeys",
    "supportedWriteCharacters",
    "write",
]
