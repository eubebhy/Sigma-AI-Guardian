# pyright: reportPrivateUsage=false
"""Kiểm thử fake và tiện ích manual của key listener.

File path: `tests/test_key_listener.py`.
Input: mode `fake`, `mock`, `smoke` hoặc `real`; real nhận `logger --kb --mouse`.
Output: unittest xác nhận event Linux/Windows; real in event đến khi Ctrl+C.
Nguyên lý: fake thay thế evdev, pynput; real chỉ đọc device input Linux khi được gọi
có chủ đích. Lệnh cũ `test_input_controller.py real logger` chuyển tiếp đến đây.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import os
import sys
import threading
import unittest
from collections.abc import Callable, Iterator, Sequence
from threading import Thread
from types import ModuleType
from typing import Any, cast
from unittest import mock
from unittest.mock import patch

from test_support import add_source_path, run_module, test_modes

add_source_path()

try:
    from evdev import ecodes
    from utils import key_listener
    from utils.key_listener import linux as linux_listener
except ModuleNotFoundError:
    _linux_fake_tests_available = False
    ecodes = cast(Any, None)
    key_listener = cast(Any, None)
    linux_listener = cast(Any, None)
else:
    _linux_fake_tests_available = True


class _InvalidCommandError(Exception):
    """Báo input CLI logger không hợp lệ trước khi đọc event thật."""


class _PrerequisiteError(Exception):
    """Báo Linux, quyền hoặc input device chưa sẵn sàng."""


def _parse_logger_arguments(arguments: Sequence[str]) -> tuple[bool, bool]:
    keyboard = "--kb" in arguments
    mouse = "--mouse" in arguments
    invalid = set(arguments).difference({"--kb", "--mouse"})
    if invalid:
        raise _InvalidCommandError(f"unknown logger option: {sorted(invalid)[0]}")
    if not keyboard and not mouse:
        raise _InvalidCommandError("logger requires --kb and/or --mouse")
    return keyboard, mouse


def _preflight_logger() -> None:
    if not sys.platform.startswith("linux"):
        raise _PrerequisiteError("real input commands require Linux")
    if not os.path.isdir("/dev/input"):
        raise _PrerequisiteError("missing /dev/input")
    devices = [
        os.path.join("/dev/input", name)
        for name in os.listdir("/dev/input")
        if name.startswith("event")
    ]
    if not devices:
        raise _PrerequisiteError("no /dev/input/event* device found")
    if not any(os.access(device, os.R_OK) for device in devices):
        raise _PrerequisiteError("read permission required for /dev/input/event*")


def _log_events(keyboard: bool, mouse: bool) -> None:
    stop_event = threading.Event()
    keyboard_thread: Thread | None = None
    try:
        if keyboard and mouse:
            keyboard_thread = Thread(
                target=_log_keyboard,
                args=(stop_event,),
                daemon=True,
            )
            keyboard_thread.start()
            _log_mouse(stop_event)
        elif keyboard:
            _log_keyboard(stop_event)
        else:
            _log_mouse(stop_event)
    finally:
        stop_event.set()
        if keyboard_thread is not None:
            keyboard_thread.join()


def _log_keyboard(stop_event: threading.Event) -> None:
    for event in key_listener.listen_keys(stop_event=stop_event):
        print("kb:", event, flush=True)


def _log_mouse(stop_event: threading.Event) -> None:
    for event in key_listener.listen_mice(stop_event=stop_event):
        print("mouse:", event, flush=True)


def run_real(
    arguments: Sequence[str],
    error_prefix: str = "key_listener",
) -> int:
    """Chạy logger Linux manual; 2 invalid/prerequisite, 1 action error."""

    values = tuple(arguments)
    try:
        if not values or values[0] != "logger":
            raise _InvalidCommandError("real requires logger")
        keyboard, mouse = _parse_logger_arguments(values[1:])
        _preflight_logger()
        print("Logging events. Press Ctrl+C to stop.", flush=True)
        _log_events(keyboard, mouse)
        return 0
    except _InvalidCommandError as error:
        print(f"[{error_prefix}][real][invalid] {error}", file=sys.stderr)
        return 2
    except _PrerequisiteError as error:
        print(f"[{error_prefix}][real][prerequisite] {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Logging stopped.", flush=True)
        return 0
    except Exception as error:
        print(f"[{error_prefix}][real][action] {error}", file=sys.stderr)
        return 1


class KeyListenerRealCommandFakeTests(unittest.TestCase):
    def test_logger_stops_cleanly_after_keyboard_interrupt(self) -> None:
        output = io.StringIO()
        with (
            patch(__name__ + "._preflight_logger"),
            patch(__name__ + "._log_events", side_effect=KeyboardInterrupt),
            contextlib.redirect_stdout(output),
        ):
            result = run_real(("logger", "--kb"))

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue().splitlines(), [
            "Logging events. Press Ctrl+C to stop.", "Logging stopped.",
        ])

    def test_combined_logger_stops_keyboard_thread_after_mouse_exits(self) -> None:
        keyboard_started = threading.Event()
        keyboard_stopped = threading.Event()

        def log_keyboard(stop_event: threading.Event) -> None:
            keyboard_started.set()
            stop_event.wait()
            keyboard_stopped.set()

        def log_mouse(_: threading.Event) -> None:
            self.assertTrue(keyboard_started.wait(timeout=1.0))

        with (
            patch(__name__ + "._log_keyboard", side_effect=log_keyboard),
            patch(__name__ + "._log_mouse", side_effect=log_mouse),
        ):
            _log_events(keyboard=True, mouse=True)

        self.assertTrue(keyboard_stopped.is_set())


class _FakeEvent:
    def __init__(self, event_type: int, code: int, value: int) -> None:
        self.type = event_type
        self.code = code
        self.value = value


class _FakeInputDevice:
    def __init__(
        self,
        events: list[_FakeEvent],
        capabilities: dict[int, list[int]] | None = None,
    ) -> None:
        self._events = events
        self._capabilities = capabilities or {}

    def fileno(self) -> int:
        return 0

    def capabilities(self, verbose: bool = False, absinfo: bool = True) -> object:
        return self._capabilities

    def read(self) -> Iterator[_FakeEvent]:
        return iter(self._events)


@unittest.skipUnless(
    _linux_fake_tests_available,
    "Linux fake tests require Linux input dependencies",
)
class LinuxListenerFakeTests(unittest.TestCase):
    @test_modes("smoke")
    def test_public_facade_exports_listener_operations(self) -> None:
        self.assertTrue(callable(key_listener.listen_keys))
        self.assertTrue(callable(key_listener.listen_mice))
        self.assertTrue(callable(key_listener.get_num_lock_state))

    def test_listener_normalizes_and_validates_devices(self) -> None:
        keyboard = _FakeInputDevice([_FakeEvent(ecodes.EV_KEY, ecodes.KEY_A, 1)])
        linux_listener._keyboards = [keyboard]
        with patch.object(
            linux_listener.select,
            "select",
            return_value=([keyboard], [], []),
        ):
            self.assertEqual(next(linux_listener.listen_keys()), ("KEY_A", "down"))
        mouse = _FakeInputDevice([
            _FakeEvent(ecodes.EV_KEY, ecodes.BTN_LEFT, 0),
            _FakeEvent(ecodes.EV_REL, ecodes.REL_X, 12),
        ])
        linux_listener._mice = [mouse]
        with patch.object(
            linux_listener.select,
            "select",
            return_value=([mouse], [], []),
        ):
            events = linux_listener.listen_mice()
            self.assertEqual(next(events), ("BTN_LEFT", "up"))
            self.assertEqual(next(events), ("REL_X", 12))
        capabilities = {ecodes.EV_KEY: list(linux_listener._LETTER_CODES)}
        self.assertTrue(linux_listener._is_keyboard(_FakeInputDevice([], capabilities)))
        with patch.object(linux_listener, "_get_keyboards", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "No Linux keyboard"):
                next(linux_listener.listen_keys())

    def test_listener_stops_before_waiting_when_stop_event_is_set(self) -> None:
        stop_event = threading.Event()
        stop_event.set()

        with patch.object(linux_listener.select, "select") as select:
            events = linux_listener.listen_keys(stop_event=stop_event)
            with self.assertRaises(StopIteration):
                next(events)

        select.assert_not_called()


class _FakeKey:
    def __init__(
        self,
        char: str | None = None,
        name: str | None = None,
        vk: int | None = None,
    ) -> None:
        self.char = char
        self.name = name
        self.vk = vk


class _FakeButton:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakePynputListener:
    def __init__(self, callbacks: dict[str, object]) -> None:
        self.callbacks = callbacks
        self.thread_alive = False
        self.stop_calls = 0
        self.join_calls = 0
        self.on_start: Callable[[_FakePynputListener], None] | None = None

    def start(self) -> None:
        return None

    def wait(self) -> None:
        self.thread_alive = True
        if self.on_start is not None:
            self.on_start(self)

    def is_alive(self) -> bool:
        return self.thread_alive

    def stop(self) -> None:
        self.stop_calls += 1
        self.thread_alive = False

    def join(self, timeout: float | None = None) -> None:
        del timeout
        self.join_calls += 1

    def emit(self, name: str, *arguments: object) -> None:
        cast(Callable[..., None], self.callbacks[name])(*arguments)


class _FakePynputModule(ModuleType):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.listener: _FakePynputListener | None = None

    def Listener(self, **callbacks: object) -> _FakePynputListener:
        self.listener = _FakePynputListener(callbacks)
        return self.listener


class WindowListenerFakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.keyboard = _FakePynputModule("pynput.keyboard")
        self.mouse = _FakePynputModule("pynput.mouse")
        sys.modules.pop("utils.key_listener.window", None)
        actual = importlib.import_module

        def import_fake(name: str, package: str | None = None) -> ModuleType:
            if name == "pynput.keyboard":
                return self.keyboard
            if name == "pynput.mouse":
                return self.mouse
            return actual(name, package)

        self.patch = mock.patch.object(
            importlib,
            "import_module",
            side_effect=import_fake,
        )
        self.patch.start()
        self.listener = importlib.import_module("utils.key_listener.window")

    def tearDown(self) -> None:
        self.patch.stop()
        sys.modules.pop("utils.key_listener.window", None)

    def test_normalizes_keyboard_events_and_cleanup(self) -> None:
        original = self.keyboard.Listener

        def with_events(**callbacks: object) -> _FakePynputListener:
            fake = original(**callbacks)

            def emit(active: _FakePynputListener) -> None:
                active.emit("on_press", _FakeKey(char="a"))
                active.emit("on_press", _FakeKey(char="a"))
                active.emit("on_release", _FakeKey(char="a"))
                active.emit("on_press", _FakeKey(name="ctrl_l"))
                active.emit("on_release", _FakeKey(name="ctrl_l"))

            fake.on_start = emit
            return fake

        self.keyboard.Listener = with_events  # pyright: ignore[reportAttributeAccessIssue]
        events = self.listener.listen_keys(timeout=0.001)
        self.assertEqual([next(events) for _ in range(5)], [
            ("KEY_A", "down"), ("KEY_A", "hold"), ("KEY_A", "up"),
            ("KEY_LEFTCTRL", "down"), ("KEY_LEFTCTRL", "up"),
        ])
        events.close()
        fake = self.keyboard.listener
        assert fake is not None
        self.assertEqual((fake.stop_calls, fake.join_calls), (1, 1))

    def test_normalizes_mouse_buttons_motion_and_scroll(self) -> None:
        original = self.mouse.Listener

        def with_events(**callbacks: object) -> _FakePynputListener:
            fake = original(**callbacks)

            def emit(active: _FakePynputListener) -> None:
                active.emit("on_move", 10, 20)
                active.emit("on_move", 13, 18)
                active.emit("on_scroll", 13, 18, 2, -1)
                for name in ("left", "right", "middle", "x1", "x2", "unknown"):
                    active.emit("on_click", 13, 18, _FakeButton(name), True)

            fake.on_start = emit
            return fake

        self.mouse.Listener = with_events  # pyright: ignore[reportAttributeAccessIssue]
        events = self.listener.listen_mice(timeout=0.001)
        self.assertEqual([next(events) for _ in range(9)], [
            ("REL_X", 3), ("REL_Y", -2), ("REL_HWHEEL", 2),
            ("REL_WHEEL", -1), ("BTN_LEFT", "down"), ("BTN_RIGHT", "down"),
            ("BTN_MIDDLE", "down"), ("BTN_BACK", "down"),
            ("BTN_FORWARD", "down"),
        ])
        events.close()

    def test_keyboard_listener_stops_hook_when_stop_event_is_set(self) -> None:
        stop_event = threading.Event()
        stop_event.set()

        events = self.listener.listen_keys(stop_event=stop_event)
        with self.assertRaises(StopIteration):
            next(events)

        fake = self.keyboard.listener
        assert fake is not None
        self.assertEqual((fake.stop_calls, fake.join_calls), (1, 1))


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
