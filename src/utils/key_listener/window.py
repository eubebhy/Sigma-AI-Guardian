"""Lắng nghe input và đọc NumLock Windows qua ``pynput``/Win32.

File path: `src/utils/key_listener/window.py`
Input: raw callback từ `pynput.keyboard` hoặc `pynput.mouse` và timeout chờ.
Output: iterator `KeyEvent` hoặc `MouseEvent` và trạng thái NumLock.
Nguyên lý: callback hook chỉ đưa raw event vào queue; generator xử lý tuần tự,
theo dõi trạng thái listener và luôn dừng/join hook trong khối ``finally``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
import ctypes
import importlib
from queue import Empty, Queue
from typing import Final, Protocol, cast

from utils.key_listener.types import KeyEvent, KeyState, MouseEvent, MouseState


class _PynputListener(Protocol):
    def start(self) -> None: ...

    def wait(self) -> None: ...

    def is_alive(self) -> bool: ...

    def stop(self) -> None: ...

    def join(self, timeout: float | None = None) -> None: ...


class _KeyboardModule(Protocol):
    def Listener(
        self,
        *,
        on_press: Callable[[object], None],
        on_release: Callable[[object], None],
    ) -> _PynputListener: ...


class _MouseModule(Protocol):
    def Listener(
        self,
        *,
        on_move: Callable[[int, int], None],
        on_click: Callable[[int, int, object, bool], None],
        on_scroll: Callable[[int, int, int, int], None],
    ) -> _PynputListener: ...


_SPECIAL_KEYS: Final[dict[str, str]] = {
    "alt": "KEY_LEFTALT",
    "alt_gr": "KEY_RIGHTALT",
    "alt_l": "KEY_LEFTALT",
    "alt_r": "KEY_RIGHTALT",
    "backspace": "KEY_BACKSPACE",
    "caps_lock": "KEY_CAPSLOCK",
    "cmd": "KEY_LEFTMETA",
    "cmd_l": "KEY_LEFTMETA",
    "cmd_r": "KEY_RIGHTMETA",
    "ctrl": "KEY_LEFTCTRL",
    "ctrl_l": "KEY_LEFTCTRL",
    "ctrl_r": "KEY_RIGHTCTRL",
    "delete": "KEY_DELETE",
    "down": "KEY_DOWN",
    "end": "KEY_END",
    "enter": "KEY_ENTER",
    "esc": "KEY_ESC",
    "home": "KEY_HOME",
    "insert": "KEY_INSERT",
    "left": "KEY_LEFT",
    "menu": "KEY_COMPOSE",
    "num_lock": "KEY_NUMLOCK",
    "page_down": "KEY_PAGEDOWN",
    "page_up": "KEY_PAGEUP",
    "pause": "KEY_PAUSE",
    "print_screen": "KEY_SYSRQ",
    "right": "KEY_RIGHT",
    "scroll_lock": "KEY_SCROLLLOCK",
    "shift": "KEY_LEFTSHIFT",
    "shift_l": "KEY_LEFTSHIFT",
    "shift_r": "KEY_RIGHTSHIFT",
    "space": "KEY_SPACE",
    "tab": "KEY_TAB",
    "up": "KEY_UP",
    **{f"f{number}": f"KEY_F{number}" for number in range(1, 25)},
}
_CHAR_KEYS: Final[dict[str, str]] = {
    " ": "SPACE",
    "-": "MINUS",
    "=": "EQUAL",
    "[": "LEFTBRACE",
    "]": "RIGHTBRACE",
    "\\": "BACKSLASH",
    ";": "SEMICOLON",
    "'": "APOSTROPHE",
    "`": "GRAVE",
    ",": "COMMA",
    ".": "DOT",
    "/": "SLASH",
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
    "_": "MINUS",
    "+": "EQUAL",
    "{": "LEFTBRACE",
    "}": "RIGHTBRACE",
    "|": "BACKSLASH",
    ":": "SEMICOLON",
    '"': "APOSTROPHE",
    "<": "COMMA",
    ">": "DOT",
    "?": "SLASH",
    "~": "GRAVE",
}
_NUMPAD_VK_KEYS: Final[dict[int, str]] = {
    **{0x60 + number: f"KEY_KP{number}" for number in range(10)},
    0x6A: "KEY_KPASTERISK",
    0x6B: "KEY_KPPLUS",
    0x6D: "KEY_KPMINUS",
    0x6E: "KEY_KPDOT",
    0x6F: "KEY_KPSLASH",
}
_BUTTONS: Final[dict[str, str]] = {
    "left": "BTN_LEFT",
    "right": "BTN_RIGHT",
    "middle": "BTN_MIDDLE",
    "x1": "BTN_BACK",
    "x2": "BTN_FORWARD",
}


def _key_name(key: object) -> str | None:
    """Chuyển key pynput đã biết sang tên evdev; unknown được bỏ qua."""

    vk = cast(int | None, getattr(key, "vk", None))
    if vk is not None and vk in _NUMPAD_VK_KEYS:
        return _NUMPAD_VK_KEYS[vk]

    char = cast(str | None, getattr(key, "char", None))
    if char is not None and len(char) == 1:
        if char.isascii() and char.isalnum():
            return f"KEY_{char.upper()}"
        mapped_char = _CHAR_KEYS.get(char)
        return f"KEY_{mapped_char}" if mapped_char is not None else None

    name = cast(str | None, getattr(key, "name", None))
    return _SPECIAL_KEYS.get(name) if name is not None else None


def _wait_timeout(timeout: float | None) -> float:
    """Giới hạn mỗi lần chờ để phát hiện hook đã chết mà không bị treo."""

    return 0.1 if timeout is None else max(0.0, min(timeout, 0.1))


def get_num_lock_state() -> bool:
    """Trả trạng thái NumLock hiện tại từ Windows user32."""

    windows_dll = getattr(ctypes, "windll")
    return bool(windows_dll.user32.GetKeyState(0x90) & 1)


def listen_keys(timeout: float | None = None) -> Iterator[KeyEvent]:
    """Sinh keyboard event `KEY_*`; timeout chỉ giới hạn từng lần chờ queue."""

    keyboard = cast(_KeyboardModule, importlib.import_module("pynput.keyboard"))
    raw_events: Queue[tuple[str, object]] = Queue()
    pressed: set[str] = set()

    def on_press(key: object) -> None:
        raw_events.put(("press", key))

    def on_release(key: object) -> None:
        raw_events.put(("release", key))

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    joined = False
    try:
        listener.wait()
        while True:
            if not listener.is_alive() and raw_events.empty():
                joined = True
                listener.join()
                raise RuntimeError("Windows keyboard listener stopped unexpectedly")
            try:
                action, key = raw_events.get(timeout=_wait_timeout(timeout))
            except Empty:
                continue

            name = _key_name(key)
            if name is None:
                continue
            if action == "press":
                state: KeyState = "hold" if name in pressed else "down"
                pressed.add(name)
            else:
                state = "up"
                pressed.discard(name)
            yield name, state
    finally:
        listener.stop()
        if not joined:
            listener.join()


def listen_mice(timeout: float | None = None) -> Iterator[MouseEvent]:
    """Sinh button, relative motion và scroll event theo đúng thứ tự callback."""

    mouse = cast(_MouseModule, importlib.import_module("pynput.mouse"))
    raw_events: Queue[tuple[object, ...]] = Queue()
    previous_position: tuple[int, int] | None = None

    def on_move(x: int, y: int) -> None:
        raw_events.put(("move", x, y))

    def on_click(x: int, y: int, button: object, pressed: bool) -> None:
        raw_events.put(("click", x, y, button, pressed))

    def on_scroll(x: int, y: int, dx: int, dy: int) -> None:
        raw_events.put(("scroll", x, y, dx, dy))

    listener = mouse.Listener(
        on_move=on_move,
        on_click=on_click,
        on_scroll=on_scroll,
    )
    listener.start()
    joined = False
    try:
        listener.wait()
        while True:
            if not listener.is_alive() and raw_events.empty():
                joined = True
                listener.join()
                raise RuntimeError("Windows mouse listener stopped unexpectedly")
            try:
                raw_event = raw_events.get(timeout=_wait_timeout(timeout))
            except Empty:
                continue

            action = cast(str, raw_event[0])
            if action == "move":
                position = cast(tuple[int, int], raw_event[1:3])
                if previous_position is not None:
                    dx = position[0] - previous_position[0]
                    dy = position[1] - previous_position[1]
                    if dx:
                        yield "REL_X", dx
                    if dy:
                        yield "REL_Y", dy
                previous_position = position
            elif action == "scroll":
                dx, dy = cast(tuple[int, int], raw_event[3:5])
                if dx:
                    yield "REL_HWHEEL", dx
                if dy:
                    yield "REL_WHEEL", dy
            elif action == "click":
                button = raw_event[3]
                button_name = cast(str | None, getattr(button, "name", None))
                code = _BUTTONS.get(button_name) if button_name is not None else None
                if code is not None:
                    state: MouseState = "down" if cast(bool, raw_event[4]) else "up"
                    yield code, state
    finally:
        listener.stop()
        if not joined:
            listener.join()


__all__ = ["get_num_lock_state", "listen_keys", "listen_mice"]
