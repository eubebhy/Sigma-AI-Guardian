# pyright: reportPrivateUsage=false
"""Kiểm thử fake/mock và tiện ích manual của input controller.

File path: `tests/test_input_controller.py`.
Input: mode `fake`, `mock`, `smoke` hoặc `real`; real nhận `control` hay `logger`.
Output: unittest xác nhận contract control Linux/Windows; real in chuẩn bị, action
và result. Lệnh `logger` được chuyển tiếp đến `test_key_listener.py` để giữ command
manual cũ.
Nguyên lý: fake thay thế UInput và pydirectinput; real chỉ dùng Linux control facade.

Lệnh control: `./.pyvenv/bin/python tests/test_input_controller.py real control
--move-to 500 300 --click left --write Hello --press enter`. Các flag legacy theo
thứ tự là `--key-down KEY`, `--key-up KEY`, `--press KEY`, `--write TEXT`,
`--mouse-down BUTTON`, `--mouse-up BUTTON`, `--click BUTTON`,
`--spam-click BUTTON COUNT`, `--move-to X Y`, `--move-rel X Y`, `--scroll AMOUNT`,
`--side-scroll AMOUNT`, `--position`, `--delay SECONDS`, `--list-keys`.
Lệnh logger: `./.pyvenv/bin/python tests/test_input_controller.py real logger
--kb --mouse`; dừng có chủ đích bằng Ctrl+C. Control cần Linux GNOME on Xorg, quyền
ghi `/dev/uinput`, X11 qua `$DISPLAY` và binary `xinput`. Logger chỉ cần Linux cùng
quyền đọc `/dev/input/event*` (thường chạy bằng `sudo` hoặc user thuộc group
`input`). Control tạo virtual keyboard/mouse và phát input thật; logger đọc event
thật, nên không chạy hai lệnh này trong automated test.
"""

from __future__ import annotations

import code
import importlib
import os
import shutil
import sys
import traceback
import unittest
from collections.abc import Callable, Sequence
from types import ModuleType
from typing import Any, ClassVar, cast
from unittest.mock import Mock, patch

from test_support import add_source_path, run_module, test_modes

add_source_path()

if not sys.platform.startswith("linux"):
    raise ModuleNotFoundError
from evdev import ecodes
from agent.platform.linux.input_controller import LinuxInput
from agent.platform.linux.input_controller import sendinput_mouse
from agent.platform.linux.input_controller import utils as linux_utils
from device_controller.input_controller import Input
from utils import key_listener

_linux_fake_tests_available = True
linux_api = LinuxInput()

_BACKEND_API = (
    "click",
    "keyDown",
    "keyUp",
    "mouseDown",
    "mouseUp",
    "moveRel",
    "moveTo",
    "position",
    "press",
    "scroll",
    "sideScroll",
    "supportedKeys",
    "supportedWriteCharacters",
    "write",
)


class _InvalidCommandError(Exception):
    """Báo input CLI không hợp lệ trước khi thực hiện side effect."""


class _PrerequisiteError(Exception):
    """Báo Linux, quyền hoặc desktop session chưa sẵn sàng."""


def _preflight_control() -> None:
    _require_linux()
    if not os.path.exists("/dev/uinput"):
        raise _PrerequisiteError("missing /dev/uinput")
    if not os.access("/dev/uinput", os.W_OK):
        raise _PrerequisiteError("write permission required for /dev/uinput")
    if not os.environ.get("DISPLAY"):
        raise _PrerequisiteError("X11 DISPLAY is not set")
    if shutil.which("xinput") is None:
        raise _PrerequisiteError("missing required binary: xinput")
    try:
        key_listener.get_num_lock_state()
    except Exception as e:
        raise _PrerequisiteError(f"cannot connect to the X11 display: {e}") from e


def _require_linux() -> None:
    if not sys.platform.startswith("linux"):
        raise _PrerequisiteError("real input commands require Linux")


def _run_control_shell() -> None:
    """Mở Python shell với một Input resource và các method đã preload."""

    input_resource = Input()
    namespace: dict[str, object] = {
        "input": input_resource,
        "input_help": _print_input_help,
    }
    for name in _BACKEND_API:
        namespace[name] = getattr(input_resource, name)
    try:
        code.interact(
            banner=(
                "Input control shell is ready.\n"
                "Call input_help() to view available test APIs.\n"
                "Run multiple calls with ';', for example: "
                "moveTo(500, 300); click().\n"
                "Use exit(), quit(), or Ctrl+D to close Input and leave."
            ),
            local=namespace,
        )
    finally:
        input_resource.close()


def _print_input_help() -> None:
    """In hướng dẫn API điều khiển đã preload trong manual shell."""

    print(
        """# position(take_new: bool = False) -> tuple[int, int]
Return the current cursor position as (x, y). The take_new argument is retained
for API compatibility and does not change the current behavior.
Example: position()

# moveTo(x: int | None, y: int | None, duration: float = 0.0) -> None
Move the cursor to an absolute screen position. Use None to keep one axis at its
current value. Duration is the movement time in seconds.
Examples: moveTo(500, 300); moveTo(None, 400, duration=1.0)

# moveRel(x: int | None, y: int | None, duration: float = 0.0) -> None
Move the cursor relative to its current position. Positive x moves right,
positive y moves down, and None means zero movement on that axis.
Examples: moveRel(100, -50); moveRel(None, 200, duration=0.5)

# click(x: int | None = None, y: int | None = None,
#       button: Literal['primary', 'secondary', 'middle', 'forward', 'back']
#       = 'primary') -> None
Click at (x, y), or click at the current position when both coordinates are
None. primary is left click and secondary is right click.
Examples: click(); click(500, 300); click(button='secondary')

# mouseDown(button: Literal['primary', 'secondary', 'middle', 'forward',
#           'back']) -> None
Press and hold a mouse button. Call mouseUp with the same button to release it.
Example: mouseDown('primary')

# mouseUp(button: Literal['primary', 'secondary', 'middle', 'forward',
#         'back']) -> None
Release a mouse button previously held with mouseDown.
Example: mouseUp('primary')

# scroll(amount: int) -> None
Scroll vertically. A positive amount scrolls up; a negative amount scrolls down.
Examples: scroll(3); scroll(-3)

# sideScroll(amount: int) -> None
Scroll horizontally. A positive amount scrolls right; a negative amount scrolls
left.
Examples: sideScroll(3); sideScroll(-3)

# keyDown(key: str) -> None
Press and hold one supported keyboard key. Use supportedKeys() to inspect valid
key names. Call keyUp with the same key to release it.
Example: keyDown('leftctrl')

# keyUp(key: str) -> None
Release one keyboard key previously held with keyDown.
Example: keyUp('leftctrl')

# press(keys: str | Sequence[str]) -> None
Press and release one key or each key in a sequence. A sequence is processed in
order; it does not hold the keys as a chord.
Examples: press('enter'); press(['a', 'b', 'enter'])

# write(message: str, interval: float = 0.0) -> None
Type text. Interval is the delay in seconds after each character. Use
supportedWriteCharacters() to inspect characters accepted by the active backend.
Examples: write('Hello'); write('Slow text', interval=0.1)

# supportedKeys() -> tuple[str, ...]
Return all key names accepted by keyDown, keyUp, and press.
Example: supportedKeys()

# supportedWriteCharacters() -> str
Return all characters accepted by write on the active backend.
Example: supportedWriteCharacters()

# input.close() -> None
Close all resources owned by this Input. The shell closes it automatically on
exit. Do not call another input API after closing it.

Multiple calls can be executed on one line:
moveTo(500, 300); click(); write('Hello'); press('enter')
mouseDown('primary'); moveRel(100, 0); mouseUp('primary')"""
    )


def run_real(arguments: Sequence[str]) -> int:
    """Chạy control/logger Linux manual; 2 invalid/prerequisite, 1 action error."""

    values = tuple(arguments)
    try:
        if not values:
            raise _InvalidCommandError("real requires control or logger")
        if values[0] == "control":
            if len(values) != 1:
                raise _InvalidCommandError("control does not accept arguments")
            _preflight_control()
            _run_control_shell()
            return 0
        if values[0] == "logger":
            from test_key_listener import run_real as run_listener_real

            return run_listener_real(values, error_prefix="input_controller")
        raise _InvalidCommandError(f"unknown real command: {values[0]}")
    except _InvalidCommandError as error:
        print(f"[input_controller][real][invalid] {error}", file=sys.stderr)
        return 2
    except _PrerequisiteError as error:
        print(f"[input_controller][real][prerequisite] {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Logging stopped.", flush=True)
        return 0
    except Exception as error:
        print(f"[input_controller][real][action] {error}", file=sys.stderr)
        traceback.print_exc()
        return 1


class RealCommandFakeTests(unittest.TestCase):
    def test_control_shell_preloads_api_and_closes_input(self) -> None:
        input_resource = Mock()
        shell_namespace: dict[str, object] = {}

        def capture_shell(banner: str, local: dict[str, object]) -> None:
            del banner
            shell_namespace.update(local)

        with (
            patch(__name__ + ".Input", return_value=input_resource),
            patch(__name__ + "._preflight_control"),
            patch.object(code, "interact", side_effect=capture_shell),
        ):
            result = run_real(("control",))

        self.assertEqual(result, 0)
        self.assertIs(shell_namespace["input"], input_resource)
        self.assertIs(shell_namespace["input_help"], _print_input_help)
        for name in _BACKEND_API:
            self.assertIs(shell_namespace[name], getattr(input_resource, name))
        input_resource.close.assert_called_once_with()

    def test_legacy_logger_command_delegates_to_key_listener(self) -> None:
        with patch("test_key_listener.run_real", return_value=0) as logger:
            result = run_real(("logger", "--kb"))

        self.assertEqual(result, 0)
        logger.assert_called_once_with(
            ("logger", "--kb"),
            error_prefix="input_controller",
        )


class _FakeUInput:
    last_instance: ClassVar[_FakeUInput | None] = None

    def __init__(self, capabilities: dict[int, list[int]], name: str = "") -> None:
        type(self).last_instance = self
        self.capabilities = capabilities
        self.name = name
        self.writes: list[tuple[int, int, int]] = []
        self.synced = 0
        self.fd = 10
        self.closed = False

    def write(self, event_type: int, code: int, value: int) -> None:
        self.writes.append((event_type, code, value))

    def syn(self) -> None:
        self.synced += 1

    def close(self) -> None:
        self.fd = -1
        self.closed = True


def _load_linux_sender(module_name: str, class_name: str) -> tuple[object, _FakeUInput]:
    sys.modules.pop(module_name, None)
    _FakeUInput.last_instance = None
    with (
        patch.object(linux_utils, "UInput", _FakeUInput),
        patch.object(linux_utils, "_wait_for_xinput_device") as wait,
        patch("agent.platform.linux.input_controller.sendinput_mouse.subprocess.run"),
    ):
        module = importlib.import_module(module_name)
        assert _FakeUInput.last_instance is None
        sender = cast(Callable[[], object], getattr(module, class_name))()
        cast(Callable[[], object], getattr(sender, "get_ui"))()
    fake = _FakeUInput.last_instance
    assert fake is not None
    wait.assert_called_once_with(fake.name)
    return sender, fake


@unittest.skipUnless(
    _linux_fake_tests_available,
    "Linux fake tests require Linux input dependencies",
)
class LinuxFakeTests(unittest.TestCase):
    @test_modes("fake", "mock", "smoke")
    def test_input_object_owns_and_closes_backend(self) -> None:
        from agent.platform.linux import input_controller

        input_resource = input_controller.LinuxInput()
        with (
            patch.object(input_resource._keyboard, "close") as close_keyboard,
            patch.object(input_resource._mouse, "close") as close_mouse,
        ):
            self.assertTrue(callable(input_resource.click))
            input_resource.close()
            input_resource.close()
            with self.assertRaisesRegex(RuntimeError, "Input is closed"):
                input_resource.position()

        close_keyboard.assert_called_once_with()
        close_mouse.assert_called_once_with()
        self.assertIsNone(input_resource._keyboard)
        self.assertIsNone(input_resource._mouse)

    @test_modes("smoke")
    def test_public_package_exports_only_input_class(self) -> None:
        import device_controller.input_controller as input_package

        self.assertEqual(input_package.__all__, ["Input"])
        for name in _BACKEND_API:
            self.assertFalse(hasattr(input_package, name))

    @test_modes("fake", "mock", "smoke")
    def test_public_input_uses_supplied_backend(self) -> None:
        backend = Mock()
        first = Input(backend)
        second = Input(backend)
        self.assertIsNot(first, second)
        self.assertIs(cast(Any, first)._backend, backend)
        self.assertIs(cast(Any, second)._backend, backend)

    @test_modes("fake", "mock", "smoke")
    def test_public_input_delegates_and_releases_backend(self) -> None:
        backend = Mock()
        backend.position.return_value = (10, 20)
        input_resource = Input(backend)

        input_resource.click(1, 2, "secondary")
        self.assertEqual(input_resource.position(), (10, 20))
        input_resource.close()
        input_resource.close()

        backend.click.assert_called_once_with(1, 2, "secondary")
        self.assertEqual(backend.close.call_count, 2)

    @test_modes("fake", "mock", "smoke")
    def test_public_input_uses_default_backend(self) -> None:
        backend = Mock()
        with patch("agent.platform.get_default_platform_services") as get_services:
            get_services.return_value.input_controller = backend
            input_resource = Input()

        self.assertIs(cast(Any, input_resource)._backend, backend)
        input_resource.close()
        backend.close.assert_called_once_with()

    @test_modes("fake", "mock", "smoke")
    def test_public_input_retains_backend_when_cleanup_fails(self) -> None:
        backend = Mock()
        backend.close.side_effect = [RuntimeError("cleanup failed"), None]
        input_resource = Input(backend)

        with self.assertRaisesRegex(RuntimeError, "cleanup failed"):
            input_resource.close()
        input_resource.close()

        self.assertEqual(backend.close.call_count, 2)

    def test_keyboard_capabilities_and_events(self) -> None:
        keyboard, fake = _load_linux_sender(
            "agent.platform.linux.input_controller.sendinput_kb", "KeyboardInput"
        )
        self.assertTrue(fake.name.startswith("Sigma Virtual Keyboard "))
        self.assertEqual(fake.capabilities[ecodes.EV_REP], [])
        for code in (ecodes.KEY_A, ecodes.KEY_Z, ecodes.KEY_F1, ecodes.KEY_KPENTER):
            self.assertIn(code, fake.capabilities[ecodes.EV_KEY])
        cast(Any, keyboard).keyDown("a")
        cast(Any, keyboard).keyUp("a")
        cast(Any, keyboard).press("a")
        self.assertEqual(
            fake.writes,
            [(ecodes.EV_KEY, ecodes.KEY_A, 1), (ecodes.EV_KEY, ecodes.KEY_A, 0)] * 2,
        )
        self.assertEqual(fake.synced, 4)

    def test_uinput_manager_replaces_dead_cached_device(self) -> None:
        old_ui = _FakeUInput({}, "old")
        replacement = _FakeUInput({}, "replacement")
        manager = linux_utils.UInputManager("Test Device", {})
        with (
            patch.object(linux_utils, "create_ui", side_effect=[old_ui, replacement]),
            patch.object(
                linux_utils.time, "monotonic", side_effect=[0.0, 4.9, 5.1, 10.2]
            ),
            patch.object(linux_utils, "ui_alive", side_effect=[True, False]),
        ):
            self.assertIs(manager.get_ui(), old_ui)
            self.assertIs(manager.get_ui(), old_ui)
            self.assertIs(manager.get_ui(), old_ui)
            self.assertIs(manager.get_ui(), replacement)
        self.assertTrue(old_ui.closed)

    def test_linux_exports_all_public_operations(self) -> None:
        for name in (
            "keyDown",
            "keyUp",
            "press",
            "write",
            "click",
            "moveTo",
            "moveRel",
        ):
            self.assertTrue(callable(getattr(linux_api, name)))

    def test_mouse_capabilities_motion_and_scrolling(self) -> None:
        mouse, fake = _load_linux_sender(
            "agent.platform.linux.input_controller.sendinput_mouse", "MouseInput"
        )
        self.assertEqual(
            fake.capabilities[ecodes.EV_KEY],
            [
                ecodes.BTN_LEFT,
                ecodes.BTN_RIGHT,
                ecodes.BTN_MIDDLE,
                ecodes.BTN_EXTRA,
                ecodes.BTN_SIDE,
            ],
        )
        with patch.object(mouse, "position", return_value=(10, 20)):
            cast(Any, mouse).moveTo(15, 17)
        cast(Any, mouse).scroll(-2)
        cast(Any, mouse).sideScroll(3)
        self.assertEqual(
            fake.writes,
            [
                (ecodes.EV_REL, ecodes.REL_X, 5),
                (ecodes.EV_REL, ecodes.REL_Y, -3),
                (ecodes.EV_REL, ecodes.REL_WHEEL, -2),
                (ecodes.EV_REL, ecodes.REL_HWHEEL, 3),
            ],
        )

    def test_mouse_relative_duration_and_none_axis(self) -> None:
        mouse, fake = _load_linux_sender(
            "agent.platform.linux.input_controller.sendinput_mouse", "MouseInput"
        )
        with patch.object(sendinput_mouse.time, "sleep") as sleep:
            cast(Any, mouse).moveRel(10, 0, duration=0.2)
            cast(Any, mouse).moveRel(None, 1)
        self.assertEqual(
            fake.writes[:4],
            [
                (ecodes.EV_REL, ecodes.REL_X, 5),
                (ecodes.EV_REL, ecodes.REL_Y, 0),
                (ecodes.EV_REL, ecodes.REL_X, 5),
                (ecodes.EV_REL, ecodes.REL_Y, 0),
            ],
        )
        self.assertEqual(sleep.call_args_list, [((0.1,),), ((0.1,),)])


class _FakeDirectInput(ModuleType):
    def __init__(self) -> None:
        super().__init__("pydirectinput")
        self.calls: list[tuple[object, ...]] = []
        self.KEYBOARD_MAPPING = {"a": 1, "A": 1, "ctrlleft": 1}

    def keyDown(self, key: str, *, _pause: bool = True) -> bool:
        self.calls.append(("down", key, _pause))
        return True

    def keyUp(self, key: str, *, _pause: bool = True) -> bool:
        self.calls.append(("up", key, _pause))
        return True

    def press(self, keys: object, *, _pause: bool = True) -> bool:
        self.calls.append(("press", keys, _pause))
        return True

    def write(self, text: str, **options: object) -> None:
        self.calls.append(("write", text, options.get("_pause")))

    def click(
        self, x: int | None = None, y: int | None = None, **options: object
    ) -> None:
        self.calls.append(("click", x, y, options.get("button"), options.get("_pause")))

    def mouseDown(self, **options: object) -> None:
        self.calls.append(("down", options.get("button"), options.get("_pause")))

    def mouseUp(self, **options: object) -> None:
        self.calls.append(("up", options.get("button"), options.get("_pause")))

    def position(self) -> tuple[int, int]:
        self.calls.append(("position",))
        return 10, 20

    def moveTo(self, x: int, y: int, **options: object) -> None:
        self.calls.append(
            ("moveTo", x, y, options.get("duration"), options.get("_pause"))
        )

    def moveRel(self, x: int, y: int, **options: object) -> None:
        self.calls.append(
            ("moveRel", x, y, options.get("duration"), options.get("_pause"))
        )

    def scroll(self, amount: int, **options: object) -> None:
        self.calls.append(("scroll", amount, options.get("_pause")))

    def hscroll(self, amount: int, **options: object) -> None:
        self.calls.append(("hscroll", amount, options.get("_pause")))


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class WindowFakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = _FakeDirectInput()
        sys.modules["pydirectinput"] = self.fake
        for name in (
            "agent.platform.windows.input_controller",
            "agent.platform.windows.input_controller.sendinput_kb",
            "agent.platform.windows.input_controller.sendinput_mouse",
        ):
            sys.modules.pop(name, None)

    def tearDown(self) -> None:
        sys.modules.pop("pydirectinput", None)

    @test_modes("fake", "mock", "smoke")
    def test_input_object_can_be_closed(self) -> None:
        from agent.platform.windows import input_controller

        input_resource = input_controller.WindowsInput()
        self.assertTrue(callable(input_resource.click))
        input_resource.close()
        input_resource.close()
        with self.assertRaisesRegex(RuntimeError, "Input is closed"):
            input_resource.position()

    def test_backend_is_internal_and_lazy(self) -> None:
        package_name = "agent.platform.windows.input_controller"
        for name in ("pydirectinput",):
            sys.modules.pop(name, None)
        window = importlib.import_module(package_name)
        self.assertEqual(window.__all__, [])

    def test_keyboard_delegates_and_normalizes_names(self) -> None:
        keyboard = importlib.import_module(
            "agent.platform.windows.input_controller.sendinput_kb"
        )
        keyboard.keyDown("leftctrl")
        keyboard.keyUp("leftctrl")
        keyboard.press(["a", "enter"])
        keyboard.write("A!")
        self.assertEqual(
            self.fake.calls,
            [
                ("down", "ctrlleft", False),
                ("up", "ctrlleft", False),
                ("press", ("a", "enter"), False),
                ("write", "A!", False),
            ],
        )
        self.assertIn("leftctrl", keyboard.supportedKeys())
        self.assertIn("A", keyboard.supportedWriteCharacters())

    def test_mouse_delegates_all_operations(self) -> None:
        mouse = importlib.import_module(
            "agent.platform.windows.input_controller.sendinput_mouse"
        )
        mouse.click(button="back")
        mouse.mouseDown("forward")
        mouse.mouseUp("middle")
        self.assertEqual(mouse.position(take_new=True), (10, 20))
        mouse.moveTo(15, 13, duration=0.6)
        mouse.moveRel(0, 0, duration=0.9)
        mouse.scroll(-3)
        mouse.sideScroll(2)
        self.assertEqual(
            self.fake.calls,
            [
                ("click", None, None, "x1", False),
                ("down", "x2", False),
                ("up", "middle", False),
                ("position",),
                ("moveTo", 15, 13, 0.6, False),
                ("moveRel", 0, 0, 0.9, False),
                ("scroll", -3, False),
                ("hscroll", 2, False),
            ],
        )


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
