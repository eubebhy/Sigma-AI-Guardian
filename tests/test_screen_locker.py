# pyright: reportPrivateUsage=false, reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportArgumentType=false, reportAttributeAccessIssue=false
"""Unit test lifecycle screen locker va mode khoa man hinh that.

File path: ``tests/test_screen_locker.py``.
Input: safe mode dùng fake UI/input; mode real nhận ``lock DELAY SECONDS``.
Output: mode real in countdown, trạng thái lock/unlock và cleanup cuối cùng. Chỉ in
``State: unlocked`` khi `unlock()` hoàn tất; exception cleanup được in ra stderr.
Nguyên lý: chờ ``DELAY`` giây trước khi khóa, giữ khóa ``SECONDS`` giây rồi gọi
``unlock()``; ``finally`` luôn gọi lại unlock để dọn input và overlay nếu có lỗi.
Nếu cleanup raise lỗi, command in lỗi và trả exit code 1.

Real usage dùng bởi ``--help``:
``./.pyvenv/bin/python tests/test_screen_locker.py real lock DELAY SECONDS``
Ví dụ: ``./.pyvenv/bin/python tests/test_screen_locker.py real lock 3 15``.

Prerequisites: desktop session cục bộ có Tkinter, Pillow, monitor khả dụng và quyền
chặn input theo platform. Side effects: sau DELAY, toàn bộ màn hình bị phủ overlay và
input bị chặn trong tối đa SECONDS; lỗi UI hoặc ngắt lệnh vẫn yêu cầu unlock trong
``finally``. Không chạy mode real trong suite an toàn.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import sys
import threading
import time
import traceback
from typing import NoReturn
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont


from test_support import add_source_path, run_module, test_modes


add_source_path()

from device_controler.screen_capture import ScreenRegion
from device_controler import screenlocker


_TEST_HEADER_TEXT = "TEST SCREEN LOCK"
_TEST_BODY_TEXT = (
    "Đây là test, bạn nên thấy cursor đã bị ẩn và màn hình đã bị khóa, "
    "không thể thoát được."
)


class _RealArgumentParser(argparse.ArgumentParser):
    """Parser real trả lỗi để safe test không dừng process."""

    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _create_real_parser() -> argparse.ArgumentParser:
    parser = _RealArgumentParser(add_help=False)
    commands = parser.add_subparsers(dest="command", required=True)
    lock = commands.add_parser("lock", add_help=False)
    lock.add_argument("delay", type=int)
    lock.add_argument("seconds", type=int)
    return parser


def _parse_real_arguments(arguments: Sequence[str]) -> argparse.Namespace | None:
    """Đọc command real mà không tạo overlay hoặc chặn input."""

    try:
        command = _create_real_parser().parse_args(arguments)
    except (argparse.ArgumentError, ValueError):
        return None
    if command.delay < 0 or command.seconds < 0:
        return None
    return command


def _countdown(state: str, seconds: int) -> None:
    for remaining in range(seconds, 0, -1):
        print(f"{state}: {remaining}s")
        time.sleep(1)


def run_real(arguments: Sequence[str]) -> int:
    """Khóa desktop thật theo thời gian chỉ khi caller chọn mode real rõ ràng."""

    command = _parse_real_arguments(arguments)
    if command is None:
        print("Invalid real command", file=sys.stderr)
        return 2
    result = 0
    try:
        print(f"State: locking in {command.delay}s")
        _countdown("Countdown to lock", command.delay)
        print("State: locking")
        screenlocker.lock(
            header_text=_TEST_HEADER_TEXT,
            body_text=_TEST_BODY_TEXT,
        )
        print(f"State: locked for {command.seconds}s")
        _countdown("Countdown to unlock", command.seconds)
        print("State: timed unlock")
        screenlocker.unlock()
        print("State: unlocked")
    except Exception as error:
        print(f"Action failed: {error}", file=sys.stderr)
        traceback.print_exc()
        result = 1
    finally:
        try:
            screenlocker.unlock()
        except Exception as error:
            print(f"Cleanup failed: {error}", file=sys.stderr)
            traceback.print_exc()
            result = 1
        else:
            print("Cleanup: completed")
    return result


class _FakeRoot:
    def mainloop(self) -> None:
        return None

    def after(self, _: int, callback: object, *arguments: object) -> None:
        del callback, arguments

    def destroy(self) -> None:
        return None


class _FailingRoot(_FakeRoot):
    def mainloop(self) -> None:
        raise RuntimeError("UI loop failed")


class _FakeCursorOperations:
    def __init__(self) -> None:
        self.events: list[str] = []

    def hide_cursor(self) -> None:
        self.events.append("hide")

    def show_cursor(self) -> None:
        self.events.append("show")


class _FakeWindow:
    def configure(self, **options: object) -> None:
        del options

    def attributes(self, *_: object) -> None:
        return None

    def overrideredirect(self, _: bool) -> None:
        return None

    def geometry(self, _: str) -> None:
        return None


class _FakeLabel:
    def pack(self, **options: object) -> None:
        del options


class _ImmediateThread:
    def __init__(self, *, target: object, args: tuple[object, ...], **_: object) -> None:
        self._target = target
        self._args = args

    def start(self) -> None:
        assert callable(self._target)
        self._target(*self._args)

    def is_alive(self) -> bool:
        return False

    def join(self) -> None:
        return None


class _FakeInputDevice:
    operations: list[str] = []
    failed_grabs: set[str] = set()
    failed_ungrabs: set[str] = set()
    failed_closes: set[str] = set()

    def __init__(self, path: str) -> None:
        self.path = path

    def grab(self) -> None:
        _FakeInputDevice.operations.append(f"grab:{self.path}")
        if self.path in _FakeInputDevice.failed_grabs:
            raise RuntimeError(f"grab failed: {self.path}")

    def ungrab(self) -> None:
        _FakeInputDevice.operations.append(f"ungrab:{self.path}")
        if self.path in _FakeInputDevice.failed_ungrabs:
            raise RuntimeError(f"ungrab failed: {self.path}")

    def close(self) -> None:
        _FakeInputDevice.operations.append(f"close:{self.path}")
        if self.path in _FakeInputDevice.failed_closes:
            raise RuntimeError(f"close failed: {self.path}")


class ScreenLockerTests(unittest.TestCase):
    """Screen locker phải tạo overlay cho từng monitor được cung cấp."""

    @test_modes("smoke")
    def test_compatibility_input_blocker_modules_export_public_api(self) -> None:
        from utils.input_blocker import linux, window

        self.assertTrue(callable(linux.block))
        self.assertTrue(callable(linux.unblock))
        self.assertTrue(callable(window.block))
        self.assertTrue(callable(window.unblock))

    @test_modes("fake")
    def test_run_ui_creates_one_overlay_per_monitor(self) -> None:
        first_root = _FakeRoot()
        second_root = _FakeRoot()
        regions = [
            ScreenRegion(top=0, left=0, width=1920, height=1080),
            ScreenRegion(top=0, left=1920, width=1920, height=1080),
        ]
        ready_event = threading.Event()
        failed_event = threading.Event()
        stop_event = threading.Event()
        stop_event.set()

        with (
            patch.object(screenlocker.tk, "Tk", return_value=first_root) as tk_root,
            patch.object(
                screenlocker.tk,
                "Toplevel",
                return_value=second_root,
            ) as top_level,
            patch.object(screenlocker, "ScreenLockOverlay") as overlay,
            patch.object(screenlocker, "_create_lock_image", return_value=object()),
            patch.object(screenlocker.input_blocker, "block"),
            patch.object(screenlocker.input_blocker, "unblock"),
        ):
            screenlocker._run_ui(
                regions,
                ready_event,
                failed_event,
                stop_event,
                threading.Event(),
            )

        self.assertEqual(tk_root.call_count, 1)
        self.assertEqual(top_level.call_count, 1)
        self.assertEqual(overlay.call_count, 2)
        self.assertTrue(ready_event.is_set())
        self.assertFalse(failed_event.is_set())

    @test_modes("fake")
    def test_run_ui_hides_and_shows_injected_cursor(self) -> None:
        region = ScreenRegion(top=0, left=0, width=100, height=100)
        ready_event = threading.Event()
        failed_event = threading.Event()
        stop_event = threading.Event()
        stop_event.set()
        cursor = _FakeCursorOperations()

        with (
            patch.object(screenlocker, "_create_windows", return_value=(_FakeRoot(), [])),
            patch.object(screenlocker.input_blocker, "block"),
            patch.object(screenlocker.input_blocker, "unblock"),
        ):
            screenlocker._run_ui(
                [region],
                ready_event,
                failed_event,
                stop_event,
                threading.Event(),
                cursor_operations=cursor,
            )

        self.assertEqual(cursor.events, ["hide", "show"])

    @test_modes("fake")
    def test_create_windows_uses_custom_lock_text(self) -> None:
        region = ScreenRegion(top=0, left=0, width=100, height=100)

        with (
            patch.object(screenlocker.tk, "Tk", return_value=_FakeRoot()),
            patch.object(screenlocker, "ScreenLockOverlay"),
            patch.object(screenlocker, "_create_lock_image", return_value=object()) as image,
        ):
            screenlocker._create_windows(
                [region],
                _TEST_HEADER_TEXT,
                _TEST_BODY_TEXT,
            )

        image.assert_called_once_with(region, _TEST_HEADER_TEXT, _TEST_BODY_TEXT)

    @test_modes("fake")
    def test_parse_real_lock_accepts_delay_and_duration(self) -> None:
        command = _parse_real_arguments(("lock", "3", "15"))

        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.delay, 3)
        self.assertEqual(command.seconds, 15)

    @test_modes("fake")
    def test_parse_real_lock_rejects_negative_or_missing_duration(self) -> None:
        self.assertIsNone(_parse_real_arguments(("lock", "-1", "15")))
        self.assertIsNone(_parse_real_arguments(("lock", "3")))

    @test_modes("fake")
    def test_unlock_signals_ui_and_waits_for_exit(self) -> None:
        stop_event = threading.Event()
        screenlocker._stop_event = stop_event
        ui_exited_event = unittest.mock.MagicMock()
        ui_exited_event.wait.return_value = True
        screenlocker._ui_exited_event = ui_exited_event
        screenlocker._ui_failed_event = threading.Event()
        ui_thread = unittest.mock.MagicMock()
        screenlocker._thread = ui_thread

        with patch.object(screenlocker.input_blocker, "unblock") as unblock:
            completed = screenlocker.unlock()

        self.assertTrue(stop_event.is_set())
        unblock.assert_not_called()
        ui_exited_event.wait.assert_called_once_with(timeout=5.0)
        ui_thread.join.assert_called_once()
        self.assertTrue(completed)

    @test_modes("fake")
    def test_run_ui_cleans_input_on_the_ui_thread_when_ui_fails(self) -> None:
        region = ScreenRegion(top=0, left=0, width=100, height=100)
        ready_event = threading.Event()
        failed_event = threading.Event()
        exited_event = threading.Event()

        with (
            patch.object(screenlocker, "_create_windows", return_value=(_FailingRoot(), [])),
            patch.object(screenlocker.input_blocker, "block"),
            patch.object(screenlocker.input_blocker, "unblock") as unblock,
        ):
            screenlocker._run_ui(
                [region],
                ready_event,
                failed_event,
                threading.Event(),
                exited_event,
            )

        self.assertTrue(ready_event.is_set())
        self.assertTrue(failed_event.is_set())
        self.assertTrue(exited_event.is_set())
        unblock.assert_called_once()

    @test_modes("fake")
    def test_run_real_reports_unlock_exception(self) -> None:
        output = StringIO()
        errors = StringIO()

        with (
            patch.object(screenlocker, "lock") as lock,
            patch.object(
                screenlocker,
                "unlock",
                side_effect=(RuntimeError("UI cleanup failed"), None),
            ),
            patch(__name__ + "._countdown"),
            redirect_stdout(output),
            redirect_stderr(errors),
        ):
            result = run_real(("lock", "0", "0"))

        self.assertEqual(result, 1)
        self.assertNotIn("State: unlocked", output.getvalue())
        self.assertIn("Action failed: UI cleanup failed", errors.getvalue())
        lock.assert_called_once_with(
            header_text=_TEST_HEADER_TEXT,
            body_text=_TEST_BODY_TEXT,
        )

    @test_modes("fake")
    def test_lock_image_uses_full_screen_brand_layout(self) -> None:
        region = ScreenRegion(top=0, left=0, width=1280, height=720)

        with patch.object(
            screenlocker.screen_capture,
            "capture",
            side_effect=AssertionError("Lock screen must not capture the desktop"),
        ):
            image = screenlocker._create_lock_image(region)

        self.assertEqual(image.size, (1280, 720))
        self.assertEqual(image.getpixel((0, 719)), (171, 1, 1))

    @test_modes("fake")
    def test_font_size_uses_one_twenty_fifth_of_monitor_width(self) -> None:
        region = ScreenRegion(top=0, left=0, width=1920, height=1080)

        self.assertEqual(screenlocker._font_size(region), 76)

    @test_modes("fake")
    def test_body_font_shrinks_when_text_exceeds_monitor_height(self) -> None:
        region = ScreenRegion(top=0, left=0, width=1280, height=300)

        self.assertLess(
            screenlocker._fit_body_font_size(region, header_height=50, padding=16),
            screenlocker._font_size(region),
        )

    @test_modes("fake")
    def test_wrap_text_preserves_ascii_art_lines(self) -> None:
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        font = ImageFont.truetype(screenlocker.FONT_PATH, 16)
        art = "  title\twith tab\n /\\\n<  >\n \\_/"

        wrapped = screenlocker._wrap_text(draw, art, font, max_width=1000)

        self.assertEqual(wrapped, art)

    @test_modes("fake")
    def test_overlay_keeps_photo_image_alive_on_its_label(self) -> None:
        window = _FakeWindow()
        label = _FakeLabel()
        photo = object()
        region = ScreenRegion(top=0, left=0, width=100, height=100)

        with (
            patch.object(screenlocker.ImageTk, "PhotoImage", return_value=photo),
            patch.object(screenlocker.tk, "Label", return_value=label),
        ):
            screenlocker.ScreenLockOverlay(
                window,
                Image.new("RGB", (1, 1)),
                region,
            )

        self.assertTrue(hasattr(label, "image"))
        self.assertIs(label.image, photo)

    @test_modes("fake", "smoke")
    def test_lock_reports_ui_startup_failure(self) -> None:
        region = ScreenRegion(top=0, left=0, width=100, height=100)
        screenlocker._thread = None

        def fail_ui(
            _: list[ScreenRegion],
            ready_event: threading.Event,
            failed_event: threading.Event,
            __: threading.Event,
            ___: threading.Event,
            ____: str,
            _____: str,
            ______: object,
        ) -> None:
            failed_event.set()
            ready_event.set()
            ___.set()

        with (
            patch.object(screenlocker.screen_capture, "get_monitors", return_value=[region]),
            patch.object(screenlocker.threading, "Thread", _ImmediateThread),
            patch.object(screenlocker, "_run_ui", side_effect=fail_ui),
            patch.object(screenlocker.input_blocker, "unblock"),
        ):
            with self.assertRaisesRegex(RuntimeError, "UI"):
                screenlocker.lock()

    @test_modes("fake")
    def test_lock_raises_when_ready_ui_exits_before_input_blocks(self) -> None:
        region = ScreenRegion(top=0, left=0, width=100, height=100)
        ready_event = threading.Event()
        ready_event.set()
        failed_event = threading.Event()
        exited_event = threading.Event()
        exited_event.set()
        stop_event = threading.Event()

        def start_ui(
            _: list[ScreenRegion],
            __: str,
            ___: str,
            ____: object,
        ) -> tuple[threading.Event, threading.Event, threading.Event, threading.Event]:
            screenlocker._stop_event = stop_event
            screenlocker._ui_exited_event = exited_event
            screenlocker._ui_failed_event = failed_event
            screenlocker._thread = None
            return ready_event, failed_event, stop_event, exited_event

        with (
            patch.object(screenlocker.screen_capture, "get_monitors", return_value=[region]),
            patch.object(screenlocker, "_start_ui", side_effect=start_ui),
            patch.object(screenlocker.input_blocker, "block") as block,
            patch.object(screenlocker.input_blocker, "unblock") as unblock,
        ):
            with self.assertRaisesRegex(RuntimeError, "UI"):
                screenlocker.lock()

        block.assert_not_called()
        unblock.assert_not_called()

    @test_modes("fake")
    def test_unlock_raises_when_input_cleanup_fails(self) -> None:
        stop_event = threading.Event()
        exited_event = threading.Event()
        exited_event.set()
        screenlocker._stop_event = stop_event
        screenlocker._ui_exited_event = exited_event
        screenlocker._ui_failed_event = threading.Event()
        screenlocker._ui_failed_event.set()
        screenlocker._ui_error = RuntimeError("input cleanup failed")
        screenlocker._thread = None

        with self.assertRaisesRegex(RuntimeError, "input cleanup failed"):
            screenlocker.unlock()

        self.assertTrue(stop_event.is_set())

    @test_modes("fake")
    def test_unlock_raises_when_ui_cleanup_is_not_confirmed(self) -> None:
        stop_event = threading.Event()
        exited_event = unittest.mock.MagicMock()
        exited_event.wait.return_value = False
        screenlocker._stop_event = stop_event
        screenlocker._ui_exited_event = exited_event
        screenlocker._ui_failed_event = threading.Event()
        screenlocker._thread = None

        with patch.object(screenlocker.input_blocker, "unblock"):
            with self.assertRaisesRegex(RuntimeError, "UI cleanup"):
                screenlocker.unlock()

        self.assertTrue(stop_event.is_set())
        exited_event.wait.assert_called_once_with(timeout=5.0)

    @test_modes("fake")
    def test_failed_lock_does_not_unlock_a_newer_locker(self) -> None:
        old_stop_event = threading.Event()
        screenlocker._stop_event = threading.Event()
        screenlocker._ui_exited_event = threading.Event()
        screenlocker._ui_failed_event = threading.Event()
        screenlocker._thread = None

        with patch.object(screenlocker.input_blocker, "unblock") as unblock:
            with self.assertRaisesRegex(RuntimeError, "old lock failed"):
                screenlocker._raise_after_lock_cleanup(
                    RuntimeError("old lock failed"),
                    old_stop_event,
                )

        unblock.assert_not_called()

    @test_modes("fake")
    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux only")
    def test_linux_input_blocker_releases_after_last_owner(self) -> None:
        from agent.platform.linux import input_blocker as blocker_adapter
        from agent.platform.linux import input_blocker_backend

        blocker_adapter._block_count = 0
        first = blocker_adapter.LinuxInputBlockingOperations()
        second = blocker_adapter.LinuxInputBlockingOperations()
        with (
            patch.object(input_blocker_backend, "block") as block,
            patch.object(input_blocker_backend, "unblock") as unblock,
        ):
            first.block()
            second.block()
            first.unblock()
            unblock.assert_not_called()
            second.unblock()

        block.assert_called_once_with()
        unblock.assert_called_once_with()

    @test_modes("fake")
    @unittest.skipUnless(sys.platform == "win32", "Windows only")
    def test_windows_input_blocker_rejects_a_second_owner_thread(self) -> None:
        import agent.platform.windows as windows_platform
        from agent.platform.windows import input_blocker as blocker_adapter

        blocker_adapter._block_count = 0
        blocker_adapter._owner_thread_id = None
        first = blocker_adapter.WindowsInputBlockingOperations()
        second = blocker_adapter.WindowsInputBlockingOperations()
        errors: list[Exception] = []
        backend = unittest.mock.MagicMock()

        def block_from_other_thread() -> None:
            try:
                second.block()
            except Exception as error:
                errors.append(error)

        with patch.object(
            windows_platform,
            "input_blocker_backend",
            backend,
            create=True,
        ):
            first.block()
            thread = threading.Thread(target=block_from_other_thread)
            thread.start()
            thread.join()
            first.unblock()

        self.assertEqual(len(errors), 1)
        self.assertIn("another thread", str(errors[0]))

    @test_modes("fake")
    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux only")
    def test_linux_block_rolls_back_when_one_device_grab_fails(self) -> None:
        from agent.platform.linux import input_blocker_backend as linux_input_blocker

        _FakeInputDevice.operations = []
        _FakeInputDevice.failed_grabs = {"/dev/input/event1"}
        _FakeInputDevice.failed_ungrabs = set()
        _FakeInputDevice.failed_closes = set()

        with (
            patch.object(linux_input_blocker, "_grabbed_devices", {}),
            patch.object(
                linux_input_blocker,
                "list_devices",
                return_value=["/dev/input/event0", "/dev/input/event1"],
            ),
            patch.object(linux_input_blocker, "InputDevice", _FakeInputDevice),
        ):
            with self.assertRaisesRegex(RuntimeError, "grab failed"):
                linux_input_blocker.block()

            self.assertEqual(linux_input_blocker._grabbed_devices, {})

        self.assertEqual(
            _FakeInputDevice.operations,
            [
                "grab:/dev/input/event0",
                "grab:/dev/input/event1",
                "ungrab:/dev/input/event0",
                "close:/dev/input/event0",
                "ungrab:/dev/input/event1",
                "close:/dev/input/event1",
            ],
        )

    @test_modes("fake")
    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux only")
    def test_linux_unblock_attempts_every_release_before_raising(self) -> None:
        from agent.platform.linux import input_blocker_backend as linux_input_blocker

        _FakeInputDevice.operations = []
        _FakeInputDevice.failed_grabs = set()
        _FakeInputDevice.failed_ungrabs = {"/dev/input/event0"}
        _FakeInputDevice.failed_closes = {"/dev/input/event1"}
        first = _FakeInputDevice("/dev/input/event0")
        second = _FakeInputDevice("/dev/input/event1")

        with patch.object(
            linux_input_blocker,
            "_grabbed_devices",
            {first.path: first, second.path: second},
        ):
            with self.assertRaises(ExceptionGroup):
                linux_input_blocker.unblock()

            self.assertEqual(
                linux_input_blocker._grabbed_devices,
                {second.path: second},
            )

        self.assertEqual(
            _FakeInputDevice.operations,
            [
                "ungrab:/dev/input/event0",
                "close:/dev/input/event0",
                "ungrab:/dev/input/event1",
                "close:/dev/input/event1",
            ],
        )

    @test_modes("fake")
    def test_lock_cleans_up_ui_when_input_blocking_fails(self) -> None:
        region = ScreenRegion(top=0, left=0, width=100, height=100)
        screenlocker._thread = None
        with (
            patch.object(
                screenlocker.screen_capture,
                "get_monitors",
                return_value=[region],
            ),
            patch.object(
                screenlocker,
                "_create_windows",
                return_value=(_FakeRoot(), []),
            ),
            patch.object(screenlocker.threading, "Thread", _ImmediateThread),
            patch.object(
                screenlocker.input_blocker,
                "block",
                side_effect=RuntimeError("Input blocking failed"),
            ),
            patch.object(screenlocker.input_blocker, "unblock") as unblock,
        ):
            with self.assertRaisesRegex(RuntimeError, "Input blocking failed"):
                screenlocker.lock()

        unblock.assert_not_called()

    @test_modes("real")
    def test_manual_screen_lock_has_cleanup(self) -> None:
        try:
            screenlocker.lock()
        finally:
            screenlocker.unlock()


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
