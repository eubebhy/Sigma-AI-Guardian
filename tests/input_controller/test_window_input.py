# pyright: strict
"""Kiểm thử backend input Windows bằng dependency giả.

File path: `tests/input_controller/test_window_input.py`
Input: module gửi input Windows và module `pydirectinput` giả trong `sys.modules`.
Output: xác nhận contract bàn phím, nút chuột, cuộn và di chuyển con trỏ.
Nguyên lý: dependency giả ghi lại lời gọi để test chạy độc lập trên Linux.
"""

from __future__ import annotations

import builtins
import importlib
import inspect
import sys
import threading
import unittest
from collections.abc import Callable, Generator, Iterator
from pathlib import Path
from queue import Empty, Queue
from types import ModuleType
from typing import Protocol, cast
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class _KeyboardSender(Protocol):
    def keyDown(self, key: str) -> None: ...

    def keyUp(self, key: str) -> None: ...

    def press(self, keys: str | list[str]) -> None: ...

    def write(self, message: str, interval: float = 0.0) -> None: ...

    def supportedKeys(self) -> tuple[str, ...]: ...

    def supportedWriteCharacters(self) -> str: ...


class _MouseSender(Protocol):
    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "primary",
    ) -> None: ...

    def mouseDown(self, button: str) -> None: ...

    def mouseUp(self, button: str) -> None: ...

    def position(self, take_new: bool = False) -> tuple[int, int]: ...

    def moveTo(
        self,
        x: int | None,
        y: int | None,
        duration: float = 0.0,
    ) -> None: ...

    def moveRel(
        self,
        x: int | None,
        y: int | None,
        duration: float = 0.0,
    ) -> None: ...

    def scroll(self, amount: int) -> None: ...

    def sideScroll(self, amount: int) -> None: ...


class _WindowListener(Protocol):
    def listen_keys(
        self, timeout: float | None = None
    ) -> Iterator[tuple[str, str]]: ...

    def listen_mice(
        self, timeout: float | None = None
    ) -> Iterator[tuple[str, str | int]]: ...


class _FakeKey:
    def __init__(
        self,
        *,
        char: str | None = None,
        name: str | None = None,
        vk: int | None = None,
    ) -> None:
        self.char = char
        self.name = name
        self.vk = vk

    def __str__(self) -> str:
        return "unknown"


class _FakeButton:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakePynputListener:
    """Mô phỏng listener nền và cho phép test chủ động phát raw callback."""

    def __init__(self, callbacks: dict[str, object]) -> None:
        self.callbacks = callbacks
        self.running = False
        self.thread_alive = False
        self.started = False
        self.wait_calls = 0
        self.stop_calls = 0
        self.join_calls = 0
        self.on_start: Callable[[_FakePynputListener], None] | None = None
        self.join_error: BaseException | None = None
        self.wait_error: BaseException | None = None

    def start(self) -> None:
        self.started = True

    def wait(self) -> None:
        if not self.started:
            raise RuntimeError("Listener must be started before wait")
        self.wait_calls += 1
        if self.wait_error is not None:
            raise self.wait_error
        self.running = True
        self.thread_alive = True
        if self.on_start is not None:
            self.on_start(self)

    def is_alive(self) -> bool:
        return self.thread_alive

    def stop(self) -> None:
        self.stop_calls += 1
        self.running = False
        self.thread_alive = False

    def join(self, timeout: float | None = None) -> None:
        del timeout
        self.join_calls += 1
        if self.join_error is not None:
            raise self.join_error

    def emit(self, callback_name: str, *args: object) -> None:
        callback = cast(Callable[..., None], self.callbacks[callback_name])
        callback(*args)


class _FakePynputModule(ModuleType):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.listener: _FakePynputListener | None = None

    def Listener(self, **callbacks: object) -> _FakePynputListener:
        self.listener = _FakePynputListener(callbacks)
        return self.listener


class _FakePyDirectInput(ModuleType):
    """Ghi lại event bàn phím thay cho việc gửi input Windows thật."""

    def __init__(self) -> None:
        super().__init__("pydirectinput")
        self.calls: list[tuple[str, str, bool]] = []
        self.failed_calls: set[tuple[str, str]] = set()
        self.KEYBOARD_MAPPING = {"a": 1, "A": 1, "ctrlleft": 1}

    def keyDown(self, key: str, *, _pause: bool = True) -> bool:
        self.calls.append(("down", key, _pause))
        return ("down", key) not in self.failed_calls

    def keyUp(self, key: str, *, _pause: bool = True) -> bool:
        self.calls.append(("up", key, _pause))
        return ("up", key) not in self.failed_calls

    def press(self, keys: tuple[str, ...], *, _pause: bool) -> bool:
        self.calls.append(("press", " ".join(keys), _pause))
        return True

    def write(
        self,
        text: str,
        *,
        interval: float,
        auto_shift: bool,
        _pause: bool,
    ) -> None:
        del interval, auto_shift
        self.calls.append(("write", text, _pause))


class _FakeMousePyDirectInput(ModuleType):
    """Ghi lại event chuột thay cho việc gửi input Windows thật."""

    def __init__(self) -> None:
        super().__init__("pydirectinput")
        self.calls: list[tuple[object, ...]] = []
        self.current_position = (10, 20)

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        *,
        button: str,
        _pause: bool = True,
    ) -> None:
        self.calls.append(("click", x, y, button, _pause))

    def mouseDown(self, *, button: str, _pause: bool = True) -> None:
        self.calls.append(("down", button, _pause))

    def mouseUp(self, *, button: str, _pause: bool = True) -> None:
        self.calls.append(("up", button, _pause))

    def position(self) -> tuple[int, int]:
        self.calls.append(("position",))
        return self.current_position

    def moveTo(
        self,
        x: int,
        y: int,
        *,
        duration: float = 0,
        _pause: bool = True,
    ) -> None:
        self.calls.append(("moveTo", x, y, duration, _pause))

    def moveRel(
        self,
        x: int,
        y: int,
        *,
        duration: float = 0,
        _pause: bool = True,
    ) -> None:
        self.calls.append(("moveRel", x, y, duration, _pause))

    def scroll(self, clicks: int, *, _pause: bool = True) -> None:
        self.calls.append(("scroll", clicks, _pause))

    def hscroll(self, clicks: int, *, _pause: bool = True) -> None:
        self.calls.append(("hscroll", clicks, _pause))


class WindowExportTests(unittest.TestCase):
    """Kiểm tra facade Windows giữ đúng public contract của Linux."""

    def setUp(self) -> None:
        sys.modules.pop("utils.input_controller.window", None)

    def tearDown(self) -> None:
        sys.modules.pop("utils.input_controller.window", None)

    def test_exports_same_ordered_api_as_linux(self) -> None:
        linux = importlib.import_module("utils.input_controller.linux")
        window = importlib.import_module("utils.input_controller.window")

        self.assertTrue(hasattr(window, "__all__"), "Windows facade is missing")
        self.assertEqual(window.__all__, linux.__all__)
        self.assertEqual(len(window.__all__), 16)
        for name in linux.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(window, name))

    def test_export_signatures_match_linux(self) -> None:
        linux = importlib.import_module("utils.input_controller.linux")
        window = importlib.import_module("utils.input_controller.window")

        for name in linux.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(window, name), f"Missing export: {name}")
                self.assertEqual(
                    inspect.signature(getattr(window, name), eval_str=True),
                    inspect.signature(getattr(linux, name), eval_str=True),
                )

    def test_import_does_not_eagerly_import_platform_dependencies(self) -> None:
        package_name = "utils.input_controller.window"
        dependency_names = (
            "pydirectinput",
            "pynput",
            "pynput.keyboard",
            "pynput.mouse",
        )
        for name in tuple(sys.modules):
            if name == package_name or name.startswith(f"{package_name}."):
                sys.modules.pop(name)
        for name in dependency_names:
            sys.modules.pop(name, None)

        real_import = builtins.__import__
        real_import_module = importlib.import_module

        def guard_dependency(name: str) -> None:
            if name == "pydirectinput" or name == "pynput" or name.startswith(
                "pynput."
            ):
                raise AssertionError(f"Eager platform dependency import: {name}")

        def guarded_import(
            name: str,
            globals: dict[str, object] | None = None,
            locals: dict[str, object] | None = None,
            fromlist: tuple[str, ...] = (),
            level: int = 0,
        ) -> object:
            guard_dependency(name)
            return real_import(name, globals, locals, fromlist, level)

        def guarded_import_module(
            name: str, package: str | None = None
        ) -> ModuleType:
            guard_dependency(name)
            return real_import_module(name, package)

        with (
            mock.patch.object(builtins, "__import__", side_effect=guarded_import),
            mock.patch.object(
                importlib,
                "import_module",
                side_effect=guarded_import_module,
            ),
        ):
            window = importlib.import_module(package_name)

        self.assertEqual(len(window.__all__), 16)
        self.assertTrue(all(name not in sys.modules for name in dependency_names))


class WindowKeyboardTests(unittest.TestCase):
    """Kiểm tra keyboard wrapper Windows."""

    fake: _FakePyDirectInput
    sender: _KeyboardSender

    def setUp(self) -> None:
        self.fake = _FakePyDirectInput()
        sys.modules["pydirectinput"] = self.fake
        module_name = "utils.input_controller.window.sendinput_kb"
        sys.modules.pop(module_name, None)
        self.sender = cast(_KeyboardSender, importlib.import_module(module_name))

    def tearDown(self) -> None:
        sys.modules.pop("pydirectinput", None)
        sys.modules.pop("utils.input_controller.window.sendinput_kb", None)

    def test_key_events_delegate_to_pydirectinput(self) -> None:
        self.sender.keyDown("leftctrl")
        self.sender.keyUp("leftctrl")

        self.assertEqual(
            self.fake.calls,
            [("down", "ctrlleft", False), ("up", "ctrlleft", False)],
        )

    def test_press_delegates_to_pydirectinput(self) -> None:
        self.sender.press(["a", "enter"])

        self.assertEqual(self.fake.calls, [("press", "a enter", False)])

    def test_write_delegates_shift_handling_to_pydirectinput(self) -> None:
        self.sender.write("A!", interval=0)

        self.assertEqual(self.fake.calls, [("write", "A!", False)])

    def test_support_helpers_match_accepted_input(self) -> None:
        supported_keys = self.sender.supportedKeys()
        self.assertIn("leftctrl", supported_keys)
        self.assertNotIn("ctrlleft", supported_keys)

        characters = self.sender.supportedWriteCharacters()
        self.assertIn("a", characters)
        self.assertIn("A", characters)


class WindowMouseTests(unittest.TestCase):
    """Kiểm tra contract mouse sender Windows."""

    fake: _FakeMousePyDirectInput
    sender: _MouseSender

    def setUp(self) -> None:
        self.fake = _FakeMousePyDirectInput()
        sys.modules["pydirectinput"] = self.fake
        module_name = "utils.input_controller.window.sendinput_mouse"
        sys.modules.pop(module_name, None)
        self.sender = cast(_MouseSender, importlib.import_module(module_name))

    def tearDown(self) -> None:
        sys.modules.pop("pydirectinput", None)
        sys.modules.pop("utils.input_controller.window.sendinput_mouse", None)

    def test_maps_buttons_and_disables_global_pause(self) -> None:
        self.sender.click(button="back")
        self.sender.mouseDown("forward")
        self.sender.mouseUp("middle")

        self.assertEqual(
            self.fake.calls,
            [
                ("click", None, None, "x1", False),
                ("down", "x2", False),
                ("up", "middle", False),
            ],
        )

    def test_delegates_button_validation_to_pydirectinput(self) -> None:
        self.sender.click(button="invalid")
        self.sender.mouseDown("invalid")
        self.sender.mouseUp("invalid")

        self.assertEqual(
            self.fake.calls,
            [
                ("click", None, None, "invalid", False),
                ("down", "invalid", False),
                ("up", "invalid", False),
            ],
        )

    def test_scrolls_both_axes_without_global_pause(self) -> None:
        self.sender.scroll(-3)
        self.sender.sideScroll(2)

        self.assertEqual(
            self.fake.calls,
            [("scroll", -3, False), ("hscroll", 2, False)],
        )

    def test_position_accepts_take_new(self) -> None:
        self.assertEqual(self.sender.position(), (10, 20))
        self.assertEqual(self.sender.position(take_new=True), (10, 20))
        self.assertEqual(self.fake.calls, [("position",), ("position",)])

    def test_move_to_delegates_duration(self) -> None:
        self.sender.moveTo(15, 13, duration=0.6)

        self.assertEqual(
            self.fake.calls,
            [("moveTo", 15, 13, 0.6, False)],
        )

    def test_move_rel_delegates_duration(self) -> None:
        self.sender.moveRel(-4, 6, duration=1)

        self.assertEqual(
            self.fake.calls,
            [("moveRel", -4, 6, 1, False)],
        )

    def test_move_rel_accepts_zero_delta(self) -> None:
        self.sender.moveRel(0, 0, duration=0.9)

        self.assertEqual(
            self.fake.calls,
            [("moveRel", 0, 0, 0.9, False)],
        )

    def test_import_is_lazy_until_api_call(self) -> None:
        module_name = "utils.input_controller.window.sendinput_mouse"
        sys.modules.pop("pydirectinput", None)
        sys.modules.pop(module_name, None)

        sender = cast(_MouseSender, importlib.import_module(module_name))

        with mock.patch.object(
            importlib,
            "import_module",
            return_value=self.fake,
        ) as import_dependency:
            self.assertEqual(sender.position(), (10, 20))

        import_dependency.assert_called_once_with("pydirectinput")


class WindowListenerTests(unittest.TestCase):
    """Kiểm tra listener Windows bằng hook `pynput` giả, chạy được trên Linux."""

    module_name = "utils.input_controller.window.listener"
    listener: _WindowListener
    keyboard: _FakePynputModule
    mouse: _FakePynputModule

    def setUp(self) -> None:
        self.keyboard = _FakePynputModule("pynput.keyboard")
        self.mouse = _FakePynputModule("pynput.mouse")
        sys.modules.pop(self.module_name, None)

        real_import_module = importlib.import_module

        def import_fake(name: str, package: str | None = None) -> ModuleType:
            if name == "pynput.keyboard":
                return self.keyboard
            if name == "pynput.mouse":
                return self.mouse
            return real_import_module(name, package)

        self.import_patch = mock.patch.object(
            importlib, "import_module", side_effect=import_fake
        )
        self.import_module = self.import_patch.start()
        self.listener = cast(_WindowListener, importlib.import_module(self.module_name))

    def tearDown(self) -> None:
        self.import_patch.stop()
        sys.modules.pop(self.module_name, None)

    def test_normalizes_keyboard_chars_modifiers_and_repeat(self) -> None:
        def emit_keys(fake: _FakePynputListener) -> None:
            fake.emit("on_press", _FakeKey(char="a"))
            fake.emit("on_press", _FakeKey(char="a"))
            fake.emit("on_release", _FakeKey(char="a"))
            fake.emit("on_press", _FakeKey(name="ctrl_l"))
            fake.emit("on_release", _FakeKey(name="ctrl_l"))
            fake.emit("on_press", _FakeKey())

        original_listener = self.keyboard.Listener

        def listener_with_events(**callbacks: object) -> _FakePynputListener:
            fake = original_listener(**callbacks)
            fake.on_start = emit_keys
            return fake

        self.keyboard.Listener = listener_with_events  # pyright: ignore[reportAttributeAccessIssue]

        events = cast(
            Generator[tuple[str, str], None, None],
            self.listener.listen_keys(timeout=0.001),
        )
        self.assertEqual(
            [next(events) for _ in range(5)],
            [
                ("KEY_A", "down"),
                ("KEY_A", "hold"),
                ("KEY_A", "up"),
                ("KEY_LEFTCTRL", "down"),
                ("KEY_LEFTCTRL", "up"),
            ],
        )
        events.close()
        fake = self.keyboard.listener
        assert fake is not None
        self.assertEqual(fake.wait_calls, 1)

    def test_normalizes_alt_gr_as_right_alt_down_and_up(self) -> None:
        original_listener = self.keyboard.Listener

        def listener_with_alt_gr(**callbacks: object) -> _FakePynputListener:
            fake = original_listener(**callbacks)

            def emit_alt_gr(active: _FakePynputListener) -> None:
                active.emit("on_press", _FakeKey(name="alt_gr"))
                active.emit("on_release", _FakeKey(name="alt_gr"))
                active.thread_alive = False

            fake.on_start = emit_alt_gr
            return fake

        self.keyboard.Listener = listener_with_alt_gr  # pyright: ignore[reportAttributeAccessIssue]
        events = cast(
            Generator[tuple[str, str], None, None], self.listener.listen_keys()
        )
        self.assertEqual(
            [next(events), next(events)],
            [("KEY_RIGHTALT", "down"), ("KEY_RIGHTALT", "up")],
        )
        events.close()

    def test_normalizes_shifted_physical_characters(self) -> None:
        shifted = "!@#$%^&*()_+{}|:\"<>?~"
        expected_codes = (
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
            "MINUS", "EQUAL", "LEFTBRACE", "RIGHTBRACE", "BACKSLASH",
            "SEMICOLON", "APOSTROPHE", "COMMA", "DOT", "SLASH", "GRAVE",
        )
        original_listener = self.keyboard.Listener

        def listener_with_symbols(**callbacks: object) -> _FakePynputListener:
            fake = original_listener(**callbacks)

            def emit_symbols(active: _FakePynputListener) -> None:
                for char in shifted:
                    active.emit("on_press", _FakeKey(char=char))
                active.thread_alive = False

            fake.on_start = emit_symbols
            return fake

        self.keyboard.Listener = listener_with_symbols  # pyright: ignore[reportAttributeAccessIssue]
        events = cast(
            Generator[tuple[str, str], None, None], self.listener.listen_keys()
        )
        self.assertEqual(
            [next(events) for _ in shifted],
            [(f"KEY_{code}", "down") for code in expected_codes],
        )
        events.close()

    def test_vk_prioritizes_numpad_without_pressed_state_collision(self) -> None:
        original_listener = self.keyboard.Listener

        def listener_with_numpad(**callbacks: object) -> _FakePynputListener:
            fake = original_listener(**callbacks)

            def emit_keys(active: _FakePynputListener) -> None:
                active.emit("on_press", _FakeKey(char="1", vk=0x31))
                active.emit("on_press", _FakeKey(char="1", vk=0x61))
                for vk in (0x6B, 0x6A, 0x6D, 0x6E, 0x6F):
                    active.emit("on_press", _FakeKey(vk=vk))
                active.thread_alive = False

            fake.on_start = emit_keys
            return fake

        self.keyboard.Listener = listener_with_numpad  # pyright: ignore[reportAttributeAccessIssue]
        events = cast(
            Generator[tuple[str, str], None, None], self.listener.listen_keys()
        )
        self.assertEqual(
            [next(events) for _ in range(7)],
            [
                ("KEY_1", "down"),
                ("KEY_KP1", "down"),
                ("KEY_KPPLUS", "down"),
                ("KEY_KPASTERISK", "down"),
                ("KEY_KPMINUS", "down"),
                ("KEY_KPDOT", "down"),
                ("KEY_KPSLASH", "down"),
            ],
        )
        events.close()

    def test_maps_windows_special_names_to_shared_names(self) -> None:
        original_listener = self.keyboard.Listener

        def listener_with_specials(**callbacks: object) -> _FakePynputListener:
            fake = original_listener(**callbacks)

            def emit_specials(active: _FakePynputListener) -> None:
                active.emit("on_press", _FakeKey(name="menu"))
                active.emit("on_press", _FakeKey(name="print_screen"))
                active.thread_alive = False

            fake.on_start = emit_specials
            return fake

        self.keyboard.Listener = listener_with_specials  # pyright: ignore[reportAttributeAccessIssue]
        events = cast(
            Generator[tuple[str, str], None, None], self.listener.listen_keys()
        )
        self.assertEqual(
            [next(events), next(events)],
            [("KEY_COMPOSE", "down"), ("KEY_SYSRQ", "down")],
        )
        events.close()

    def test_normalizes_mouse_ordering_buttons_motion_and_scroll(self) -> None:
        original_listener = self.mouse.Listener

        def listener_with_events(**callbacks: object) -> _FakePynputListener:
            fake = original_listener(**callbacks)

            def emit_mouse(active: _FakePynputListener) -> None:
                active.emit("on_move", 10, 20)
                active.emit("on_move", 13, 18)
                active.emit("on_scroll", 13, 18, 2, -1)
                for name in ("left", "right", "middle", "x1", "x2"):
                    active.emit("on_click", 13, 18, _FakeButton(name), True)
                active.emit("on_click", 13, 18, _FakeButton("unknown"), True)

            fake.on_start = emit_mouse
            return fake

        self.mouse.Listener = listener_with_events  # pyright: ignore[reportAttributeAccessIssue]

        events = cast(
            Generator[tuple[str, str | int], None, None],
            self.listener.listen_mice(timeout=0.001),
        )
        self.assertEqual(
            [next(events) for _ in range(9)],
            [
                ("REL_X", 3),
                ("REL_Y", -2),
                ("REL_HWHEEL", 2),
                ("REL_WHEEL", -1),
                ("BTN_LEFT", "down"),
                ("BTN_RIGHT", "down"),
                ("BTN_MIDDLE", "down"),
                ("BTN_BACK", "down"),
                ("BTN_FORWARD", "down"),
            ],
        )
        events.close()

    def test_timeout_retries_until_event_arrives(self) -> None:
        original_listener = self.keyboard.Listener

        def listener_with_delayed_event(**callbacks: object) -> _FakePynputListener:
            fake = original_listener(**callbacks)

            def emit_later() -> None:
                fake.emit("on_press", _FakeKey(char="z"))
                fake.thread_alive = False

            fake.on_start = lambda _listener: threading.Timer(
                0.02, emit_later
            ).start()
            return fake

        self.keyboard.Listener = listener_with_delayed_event  # pyright: ignore[reportAttributeAccessIssue]

        self.assertEqual(
            next(self.listener.listen_keys(timeout=0.001)), ("KEY_Z", "down")
        )

    def test_listener_death_terminates_and_join_reraises_exception(self) -> None:
        original_listener = self.keyboard.Listener
        expected = RuntimeError("hook failed")

        def dead_listener(**callbacks: object) -> _FakePynputListener:
            fake = original_listener(**callbacks)

            def emit_then_die(active: _FakePynputListener) -> None:
                active.emit("on_press", _FakeKey(char="e"))
                active.thread_alive = False
                active.running = False

            fake.on_start = emit_then_die
            fake.join_error = expected
            return fake

        self.keyboard.Listener = dead_listener  # pyright: ignore[reportAttributeAccessIssue]

        events = self.listener.listen_keys(timeout=0.001)
        self.assertEqual(next(events), ("KEY_E", "down"))
        with self.assertRaisesRegex(RuntimeError, "hook failed"):
            next(events)

    def test_thread_death_is_detected_while_running_remains_true(self) -> None:
        original_listener = self.keyboard.Listener

        def dying_listener(**callbacks: object) -> _FakePynputListener:
            fake = original_listener(**callbacks)
            fake.on_start = lambda active: setattr(active, "thread_alive", False)
            return fake

        self.keyboard.Listener = dying_listener  # pyright: ignore[reportAttributeAccessIssue]
        outcomes: Queue[BaseException] = Queue()

        def consume() -> None:
            try:
                next(self.listener.listen_keys(timeout=None))
            except BaseException as error:
                outcomes.put(error)

        worker = threading.Thread(target=consume, daemon=True)
        worker.start()
        timed_out = False
        outcome: BaseException | None = None
        try:
            outcome = outcomes.get(timeout=0.2)
        except Empty:
            timed_out = True
        finally:
            fake = self.keyboard.listener
            assert fake is not None
            fake.running = False
            worker.join(timeout=0.2)

        self.assertFalse(timed_out, "Listener kept polling after its thread died")
        self.assertIsInstance(outcome, RuntimeError)
        self.assertRegex(str(outcome), "stopped unexpectedly")

    def test_wait_failure_still_stops_and_joins_listener(self) -> None:
        original_listener = self.keyboard.Listener

        def listener_with_wait_error(**callbacks: object) -> _FakePynputListener:
            fake = original_listener(**callbacks)
            fake.wait_error = RuntimeError("wait failed")
            return fake

        self.keyboard.Listener = listener_with_wait_error  # pyright: ignore[reportAttributeAccessIssue]

        with self.assertRaisesRegex(RuntimeError, "wait failed"):
            next(self.listener.listen_keys())

        fake = self.keyboard.listener
        assert fake is not None
        self.assertEqual((fake.stop_calls, fake.join_calls), (1, 1))

    def test_generator_cleanup_stops_and_joins_listener(self) -> None:
        original_listener = self.keyboard.Listener

        def live_listener(**callbacks: object) -> _FakePynputListener:
            fake = original_listener(**callbacks)
            fake.on_start = lambda active: active.emit("on_press", _FakeKey(char="q"))
            return fake

        self.keyboard.Listener = live_listener  # pyright: ignore[reportAttributeAccessIssue]
        events = cast(
            Generator[tuple[str, str], None, None],
            self.listener.listen_keys(timeout=0.001),
        )
        self.assertEqual(next(events), ("KEY_Q", "down"))
        events.close()

        fake = self.keyboard.listener
        self.assertIsNotNone(fake)
        assert fake is not None
        self.assertEqual((fake.stop_calls, fake.join_calls), (1, 1))

    def test_imports_each_pynput_backend_only_when_iteration_starts(self) -> None:
        pynput_calls = [
            call
            for call in self.import_module.call_args_list
            if cast(str, call.args[0]).startswith("pynput.")
        ]
        self.assertEqual(pynput_calls, [])

        events = self.listener.listen_mice(timeout=0.001)
        original_listener = self.mouse.Listener

        def dead_listener(**callbacks: object) -> _FakePynputListener:
            fake = original_listener(**callbacks)

            def die(active: _FakePynputListener) -> None:
                active.thread_alive = False
                active.running = False

            fake.on_start = die
            return fake

        self.mouse.Listener = dead_listener  # pyright: ignore[reportAttributeAccessIssue]
        with self.assertRaisesRegex(RuntimeError, "stopped unexpectedly"):
            next(events)

        self.assertEqual(
            [
                cast(str, call.args[0])
                for call in self.import_module.call_args_list
                if cast(str, call.args[0]).startswith("pynput.")
            ],
            ["pynput.mouse"],
        )


if __name__ == "__main__":
    unittest.main()
