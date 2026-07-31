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

import argparse
import contextlib
import io
import importlib
import os
import shutil
import sys
import time
import traceback
import unittest
from collections.abc import Callable, Sequence
from types import ModuleType
from typing import Any, ClassVar, TypeAlias, cast
from unittest.mock import patch

from test_support import add_source_path, run_module, test_modes

add_source_path()

try:
    if not sys.platform.startswith("linux"):
        raise ModuleNotFoundError
    from evdev import ecodes
    from device_controler.input_controller import linux as linux_api
    from agent.platform.linux.input_controller import sendinput_kb, sendinput_mouse
    from agent.platform.linux.input_controller import utils as linux_utils
    from device_controler.input_controller.types import MouseButton
    from utils import key_listener
except ModuleNotFoundError:
    _linux_fake_tests_available = False
    ecodes = cast(Any, None)
    linux_api = cast(Any, None)
    sendinput_kb = cast(Any, None)
    sendinput_mouse = cast(Any, None)
    linux_utils = cast(Any, None)
    MouseButton = cast(Any, None)
    key_listener = cast(Any, None)
else:
    _linux_fake_tests_available = True

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

Command: TypeAlias = tuple[str, tuple[str, ...]]
_ACTION_ARGUMENTS = {
    "--key-down": 1,
    "--key-up": 1,
    "--press": 1,
    "--write": 1,
    "--mouse-down": 1,
    "--mouse-up": 1,
    "--click": 1,
    "--spam-click": 2,
    "--move-to": 2,
    "--move-rel": 2,
    "--scroll": 1,
    "--side-scroll": 1,
    "--position": 0,
    "--delay": 1,
    "--list-keys": 0,
}
_MOUSE_BUTTONS = {"left", "right", "middle", "forward", "back"}


class _InvalidCommandError(Exception):
    """Báo input CLI không hợp lệ trước khi thực hiện side effect."""


class _PrerequisiteError(Exception):
    """Báo Linux, quyền hoặc desktop session chưa sẵn sàng."""


def _build_control_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Linux keyboard/mouse actions in flag order.",
    )
    parser.add_argument("--key-down", metavar="KEY")
    parser.add_argument("--key-up", metavar="KEY")
    parser.add_argument("--press", metavar="KEY")
    parser.add_argument("--write", metavar="TEXT")
    parser.add_argument("--mouse-down", metavar="BUTTON")
    parser.add_argument("--mouse-up", metavar="BUTTON")
    parser.add_argument("--click", metavar="BUTTON")
    parser.add_argument("--spam-click", nargs=2, metavar=("BUTTON", "COUNT"))
    parser.add_argument("--move-to", nargs=2, metavar=("X", "Y"))
    parser.add_argument("--move-rel", nargs=2, metavar=("X", "Y"))
    parser.add_argument("--scroll", metavar="AMOUNT")
    parser.add_argument("--side-scroll", metavar="AMOUNT")
    parser.add_argument("--position", action="store_true")
    parser.add_argument("--delay", metavar="SECONDS")
    parser.add_argument("--list-keys", action="store_true")
    return parser


def _parse_control_commands(arguments: Sequence[str]) -> list[Command]:
    commands: list[Command] = []
    index = 0
    while index < len(arguments):
        action = arguments[index]
        count = _ACTION_ARGUMENTS.get(action)
        if count is None:
            raise _InvalidCommandError(f"unknown action: {action}")
        values = tuple(arguments[index + 1:index + count + 1])
        if len(values) != count:
            raise _InvalidCommandError(f"{action} requires {count} value(s)")
        commands.append((action, values))
        index += count + 1
    if not commands:
        raise _InvalidCommandError("control requires at least one action")
    return commands


def _validate_control_commands(commands: Sequence[Command]) -> None:
    for action, values in commands:
        if action in {"--key-down", "--key-up", "--press"}:
            if values[0] not in linux_api.supportedKeys():
                raise _InvalidCommandError(f"unsupported key: {values[0]}")
        elif action in {"--mouse-down", "--mouse-up", "--click", "--spam-click"}:
            if values[0] not in _MOUSE_BUTTONS:
                raise _InvalidCommandError(f"unsupported mouse button: {values[0]}")
            if action == "--spam-click" and _parse_int(values[1], action) < 1:
                raise _InvalidCommandError("--spam-click COUNT must be greater than zero")
        elif action in {"--move-to", "--move-rel"}:
            _parse_int(values[0], action)
            _parse_int(values[1], action)
        elif action in {"--scroll", "--side-scroll"}:
            _parse_int(values[0], action)
        elif action == "--delay" and _parse_float(values[0], action) < 0:
            raise _InvalidCommandError("--delay SECONDS must not be negative")


def _parse_int(value: str, action: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise _InvalidCommandError(f"{action} requires an integer") from error


def _parse_float(value: str, action: str) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise _InvalidCommandError(f"{action} requires a number") from error


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
    except Exception as error:
        raise _PrerequisiteError("cannot connect to the X11 display") from error


def _require_linux() -> None:
    if not sys.platform.startswith("linux"):
        raise _PrerequisiteError("real input commands require Linux")


def _prepare_devices() -> None:
    sendinput_kb._get_ui()
    sendinput_mouse._get_ui()


def _execute_control(command: Command) -> None:
    action, values = command
    print(action, *values, flush=True)
    if action == "--write":
        linux_api.write(values[0])
    elif action == "--key-down":
        linux_api.keyDown(values[0])
    elif action == "--key-up":
        linux_api.keyUp(values[0])
    elif action == "--press":
        linux_api.press(values[0])
    elif action == "--mouse-down":
        linux_api.mouseDown(cast(MouseButton, values[0]))
    elif action == "--mouse-up":
        linux_api.mouseUp(cast(MouseButton, values[0]))
    elif action == "--click":
        linux_api.click(button=cast(MouseButton, values[0]))
    elif action == "--spam-click":
        _spam_click(cast(MouseButton, values[0]), _parse_int(values[1], action))
    elif action == "--move-to":
        linux_api.moveTo(_parse_int(values[0], action), _parse_int(values[1], action))
    elif action == "--move-rel":
        linux_api.moveRel(_parse_int(values[0], action), _parse_int(values[1], action))
    elif action == "--scroll":
        linux_api.scroll(_parse_int(values[0], action))
    elif action == "--side-scroll":
        linux_api.sideScroll(_parse_int(values[0], action))
    elif action == "--position":
        print("position:", linux_api.position(), flush=True)
    elif action == "--delay":
        time.sleep(_parse_float(values[0], action))
    else:
        print("keys:", " ".join(linux_api.supportedKeys()), flush=True)


def _spam_click(button: MouseButton, count: int) -> None:
    started = time.perf_counter()
    for _ in range(count):
        linux_api.click(button=button)
    elapsed = time.perf_counter() - started
    print(f"spam-click: {count / elapsed:.2f} CPS", flush=True)


def run_real(arguments: Sequence[str]) -> int:
    """Chạy control/logger Linux manual; 2 invalid/prerequisite, 1 action error."""

    values = tuple(arguments)
    try:
        if not values:
            raise _InvalidCommandError("real requires control or logger")
        if values[0] == "control":
            if values[1:] in {("--help",), ("-h",)}:
                _build_control_parser().print_help()
                return 0
            commands = _parse_control_commands(values[1:])
            _validate_control_commands(commands)
            _preflight_control()
            print("Preparing virtual devices", flush=True)
            _prepare_devices()
            for command in commands:
                _execute_control(command)
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
    def test_control_parser_accepts_legacy_flags_without_dependencies(self) -> None:
        values = _build_control_parser().parse_args([
            "--key-down", "a", "--move-to", "5", "6", "--position",
        ])

        self.assertEqual(values.key_down, "a")
        self.assertEqual(values.move_to, ["5", "6"])
        self.assertTrue(values.position)

    def test_control_preserves_action_order_and_reports_results(self) -> None:
        calls: list[tuple[object, ...]] = []

        def record(name: str) -> Callable[..., object]:
            def _record(*values: object, **options: object) -> object:
                calls.append((name, *values, *options.values()))
                if name == "position":
                    return 10, 20
                return None

            return _record

        output = io.StringIO()
        with (
            patch(__name__ + "._preflight_control"),
            patch(__name__ + "._prepare_devices"),
            patch.object(linux_api, "keyDown", record("keyDown")),
            patch.object(linux_api, "click", record("click")),
            patch.object(linux_api, "moveTo", record("moveTo")),
            patch.object(linux_api, "position", record("position")),
            patch.object(linux_api, "supportedKeys", return_value=["a"]),
            contextlib.redirect_stdout(output),
        ):
            result = run_real(
                ("control", "--key-down", "a", "--move-to", "5", "6",
                 "--click", "left", "--position")
            )

        self.assertEqual(result, 0)
        self.assertEqual(calls, [
            ("keyDown", "a"), ("moveTo", 5, 6), ("click", "left"),
            ("position",),
        ])
        self.assertEqual(output.getvalue().splitlines(), [
            "Preparing virtual devices", "--key-down a", "--move-to 5 6",
            "--click left", "--position", "position: (10, 20)",
        ])

    def test_control_rejects_invalid_commands_before_preparing_devices(self) -> None:
        output = io.StringIO()
        with (
            patch(__name__ + "._prepare_devices") as prepare,
            contextlib.redirect_stderr(output),
        ):
            result = run_real(("control", "--spam-click", "left", "zero"))

        self.assertEqual(result, 2)
        prepare.assert_not_called()
        self.assertIn("requires an integer", output.getvalue())

    def test_control_reports_unavailable_linux_prerequisite(self) -> None:
        output = io.StringIO()
        with (
            patch(__name__ + "._preflight_control", side_effect=_PrerequisiteError("no X11")),
            contextlib.redirect_stderr(output),
        ):
            result = run_real(("control", "--position"))

        self.assertEqual(result, 2)
        self.assertIn("no X11", output.getvalue())

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


def _load_linux_sender(module_name: str) -> tuple[ModuleType, _FakeUInput]:
    sys.modules.pop(module_name, None)
    _FakeUInput.last_instance = None
    with (
        patch.object(linux_utils, "UInput", _FakeUInput),
        patch.object(linux_utils, "_wait_for_xinput_device") as wait,
        patch("agent.platform.linux.input_controller.sendinput_mouse.subprocess.run"),
    ):
        module = importlib.import_module(module_name)
        assert _FakeUInput.last_instance is None
        cast(Callable[[], object], getattr(module, "_get_ui"))()
    fake = _FakeUInput.last_instance
    assert fake is not None
    wait.assert_called_once_with(fake.name)
    return module, fake


@unittest.skipUnless(
    _linux_fake_tests_available,
    "Linux fake tests require Linux input dependencies",
)
class LinuxFakeTests(unittest.TestCase):
    @test_modes("smoke")
    def test_control_facades_export_control_operations(self) -> None:
        from device_controler.input_controller import linux

        for name in _BACKEND_API:
            self.assertTrue(callable(getattr(linux, name)))

    def test_keyboard_capabilities_and_events(self) -> None:
        module, fake = _load_linux_sender(
            "agent.platform.linux.input_controller.sendinput_kb"
        )
        self.assertTrue(fake.name.startswith("Sigma Virtual Keyboard "))
        self.assertEqual(fake.capabilities[ecodes.EV_REP], [])
        for code in (ecodes.KEY_A, ecodes.KEY_Z, ecodes.KEY_F1, ecodes.KEY_KPENTER):
            self.assertIn(code, fake.capabilities[ecodes.EV_KEY])
        module.keyDown("a")
        module.keyUp("a")
        module.press("a")
        self.assertEqual(
            fake.writes,
            [(ecodes.EV_KEY, ecodes.KEY_A, 1), (ecodes.EV_KEY, ecodes.KEY_A, 0)]
            * 2,
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
            "keyDown", "keyUp", "press", "write", "click", "moveTo", "moveRel"
        ):
            self.assertTrue(callable(getattr(linux_api, name)))

    def test_mouse_capabilities_motion_and_scrolling(self) -> None:
        module, fake = _load_linux_sender(
            "agent.platform.linux.input_controller.sendinput_mouse"
        )
        self.assertEqual(
            fake.capabilities[ecodes.EV_KEY],
            [ecodes.BTN_LEFT, ecodes.BTN_RIGHT, ecodes.BTN_MIDDLE,
             ecodes.BTN_EXTRA, ecodes.BTN_SIDE],
        )
        with patch.object(module, "position", return_value=(10, 20)):
            module.moveTo(15, 17)
        module.scroll(-2)
        module.sideScroll(3)
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
        module, fake = _load_linux_sender(
            "agent.platform.linux.input_controller.sendinput_mouse"
        )
        with patch.object(module.time, "sleep") as sleep:
            module.moveRel(10, 0, duration=0.2)
            module.moveRel(None, 1)
        self.assertEqual(fake.writes[:4], [
            (ecodes.EV_REL, ecodes.REL_X, 5),
            (ecodes.EV_REL, ecodes.REL_Y, 0),
            (ecodes.EV_REL, ecodes.REL_X, 5),
            (ecodes.EV_REL, ecodes.REL_Y, 0),
        ])
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

    def click(self, x: int | None = None, y: int | None = None, **options: object) -> None:
        self.calls.append(("click", x, y, options.get("button"), options.get("_pause")))

    def mouseDown(self, **options: object) -> None:
        self.calls.append(("down", options.get("button"), options.get("_pause")))

    def mouseUp(self, **options: object) -> None:
        self.calls.append(("up", options.get("button"), options.get("_pause")))

    def position(self) -> tuple[int, int]:
        self.calls.append(("position",))
        return 10, 20

    def moveTo(self, x: int, y: int, **options: object) -> None:
        self.calls.append(("moveTo", x, y, options.get("duration"), options.get("_pause")))

    def moveRel(self, x: int, y: int, **options: object) -> None:
        self.calls.append(("moveRel", x, y, options.get("duration"), options.get("_pause")))

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

    def test_exports_match_linux_and_are_lazy(self) -> None:
        package_name = "agent.platform.windows.input_controller"
        for name in ("pydirectinput",):
            sys.modules.pop(name, None)
        window = importlib.import_module(package_name)
        self.assertEqual(window.__all__, list(_BACKEND_API))
        for name in _BACKEND_API:
            self.assertTrue(hasattr(window, name))

    def test_keyboard_delegates_and_normalizes_names(self) -> None:
        keyboard = importlib.import_module(
            "agent.platform.windows.input_controller.sendinput_kb"
        )
        keyboard.keyDown("leftctrl")
        keyboard.keyUp("leftctrl")
        keyboard.press(["a", "enter"])
        keyboard.write("A!")
        self.assertEqual(self.fake.calls, [
            ("down", "ctrlleft", False), ("up", "ctrlleft", False),
            ("press", ("a", "enter"), False), ("write", "A!", False),
        ])
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
        self.assertEqual(self.fake.calls, [
            ("click", None, None, "x1", False), ("down", "x2", False),
            ("up", "middle", False), ("position",),
            ("moveTo", 15, 13, 0.6, False), ("moveRel", 0, 0, 0.9, False),
            ("scroll", -3, False), ("hscroll", 2, False),
        ])


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
