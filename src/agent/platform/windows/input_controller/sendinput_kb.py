"""Wrapper tối thiểu cho keyboard API của `pydirectinput-rgx` trên Windows.

File path: `src/agent/platform/windows/input_controller/sendinput_kb.py`.
Input: key name hoặc text theo key name/layout US của `pydirectinput-rgx`.
Output: gửi keyboard event bằng WinAPI SendInput.
Nguyên lý: mỗi hàm chỉ chuyển tiếp tham số tới thư viện; thư viện chịu trách
nhiệm xử lý key, Shift, delay và lỗi input.
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from typing import Any, cast

from agent.contracts import Key


_KEY_NAMES = {
    "grave": "`",
    "minus": "-",
    "equal": "=",
    "leftbrace": "[",
    "rightbrace": "]",
    "backslash": "\\",
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
    "compose": "apps",
    "sysrq": "printscreen",
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
_SHARED_KEY_NAMES = {name: shared for shared, name in _KEY_NAMES.items()}


def _input() -> Any:
    """Import dependency Windows tại thời điểm thực sự gửi input."""

    return cast(Any, importlib.import_module("pydirectinput"))


def _key_name(key: Key) -> str:
    """Đổi các tên key chung khác tên của pydirectinput-rgx."""

    return _KEY_NAMES.get(key, key)


def keyDown(key: Key) -> None:
    """Nhấn và giữ một phím."""

    _input().keyDown(_key_name(key), _pause=False)


def keyUp(key: Key) -> None:
    """Thả một phím."""

    _input().keyUp(_key_name(key), _pause=False)


def press(keys: Key | Sequence[Key]) -> None:
    """Nhấn rồi thả tuần tự các phím."""

    key_names = (keys,) if isinstance(keys, str) else tuple(keys)
    _input().press(tuple(_key_name(key) for key in key_names), _pause=False)


def write(message: str, interval: float = 0.0) -> None:
    """Gõ text theo layout US và để thư viện tự xử lý Shift."""

    _input().write(message, interval=interval, auto_shift=True, _pause=False)


def supportedKeys() -> tuple[str, ...]:
    """Trả key name mà `pydirectinput-rgx` đang hỗ trợ."""

    mappings = cast(dict[str, object], _input().KEYBOARD_MAPPING)
    return tuple(
        _SHARED_KEY_NAMES[key] if key in _SHARED_KEY_NAMES else key
        for key in mappings
    )


def supportedWriteCharacters() -> str:
    """Trả các key name một ký tự mà thư viện đang hỗ trợ."""

    return "".join(key for key in supportedKeys() if len(key) == 1)


__all__ = [
    "keyDown",
    "keyUp",
    "press",
    "supportedKeys",
    "supportedWriteCharacters",
    "write",
]
