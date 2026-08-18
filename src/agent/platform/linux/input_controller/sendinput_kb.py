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
from agent.platform.linux.input_controller.types import Capabilities, UInputDevice
from agent.platform.linux.input_controller.utils import UInputManager
from agent.platform.linux.input_controller.kb_codes import (
    _KEY_CODES,
    _DIRECT_CHARS,
    _SHIFT_CHARS,
)

_DEVICE_NAME: Final[str] = f"Sigma Virtual Keyboard {os.getpid()}"
_CAPABILITIES: Final[Capabilities] = {
    ecodes.EV_KEY: _KEY_CODES,
    ecodes.EV_REP: [],
}


class KeyboardInput:
    """Sở hữu virtual keyboard của một input controller Linux."""

    def __init__(self) -> None:
        device_name = f"{_DEVICE_NAME} {id(self)}"
        self._ui_manager = UInputManager(device_name, _CAPABILITIES)

    def get_ui(self) -> UInputDevice:
        return self._ui_manager.get_ui()

    def keyDown(self, key: Key) -> None:
        ui = self.get_ui()
        code = getattr(ecodes, "KEY_" + key.upper())
        ui.write(ecodes.EV_KEY, code, 1)
        ui.syn()

    def keyUp(self, key: Key) -> None:
        ui = self.get_ui()
        code = getattr(ecodes, "KEY_" + key.upper())
        ui.write(ecodes.EV_KEY, code, 0)
        ui.syn()

    def press(self, keys: Key | Sequence[Key]) -> None:
        key_names = (keys,) if isinstance(keys, str) else keys
        for key in key_names:
            self.keyDown(key)
            self.keyUp(key)

    def write(self, message: str, interval: float = 0.0) -> None:
        for character in message:
            if character in _DIRECT_CHARS:
                self.press(_DIRECT_CHARS[character])
            elif character in _SHIFT_CHARS:
                self.keyDown("leftshift")
                self.press(_SHIFT_CHARS[character])
                self.keyUp("leftshift")
            else:
                raise ValueError(f"Unsupported character: {character!r}")
            if interval:
                time.sleep(interval)

    def close(self) -> None:
        self._ui_manager.close()


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


__all__ = [
    "KeyboardInput",
    "supportedKeys",
    "supportedWriteCharacters",
]
