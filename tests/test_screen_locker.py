# pyright: reportPrivateUsage=false, reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportArgumentType=false, reportAttributeAccessIssue=false
"""Unit test lifecycle screen locker va mode khoa man hinh that.

File path: ``tests/test_screen_locker.py``.
Input: safe mode dùng fake UI/input; mode real nhận ``lock DELAY SECONDS``.
Output: mode real in countdown, trạng thái lock/unlock và cleanup cuối cùng. Chỉ in
``State: unlocked`` khi overlay và input cleanup được xác nhận.
Nguyên lý: chờ ``DELAY`` giây trước khi khóa, giữ khóa ``SECONDS`` giây rồi gọi
``unlock()``; ``finally`` luôn gọi lại unlock để dọn input và overlay nếu có lỗi.
Nếu cleanup không được xác nhận trong thời hạn, command in lỗi và trả exit code 1.

Real usage dùng bởi ``--info``:
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
from typing import NoReturn
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont


from test_support import add_source_path, run_module, test_modes


add_source_path()

from device_controler.screen_capture import ScreenRegion
from device_controler import screenlocker


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
        screenlocker.lock()
        print(f"State: locked for {command.seconds}s")
        _countdown("Countdown to unlock", command.seconds)
        print("State: timed unlock")
        if screenlocker.unlock():
            print("State: unlocked")
        else:
            print("State: unlock cleanup was not confirmed", file=sys.stderr)
            result = 1
    except Exception as error:
        print(f"Action failed: {error}", file=sys.stderr)
        result = 1
    finally:
        if screenlocker.unlock():
            print("Cleanup: completed")
        else:
            print("Cleanup: UI cleanup was not confirmed", file=sys.stderr)
            result = 1
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


class ScreenLockerTests(unittest.TestCase):
    """Screen locker phải tạo overlay cho từng monitor được cung cấp."""

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

        with (
            patch.object(screenlocker.tk, "Tk", return_value=first_root) as tk_root,
            patch.object(
                screenlocker.tk,
                "Toplevel",
                return_value=second_root,
            ) as top_level,
            patch.object(screenlocker, "App") as app,
            patch.object(screenlocker, "_create_lock_image", return_value=object()),
            patch.object(screenlocker.input_blocker, "unblock"),
        ):
            screenlocker._run_ui(
                regions,
                ready_event,
                failed_event,
                threading.Event(),
                threading.Event(),
            )

        self.assertEqual(tk_root.call_count, 1)
        self.assertEqual(top_level.call_count, 1)
        self.assertEqual(app.call_count, 2)
        self.assertTrue(ready_event.is_set())
        self.assertFalse(failed_event.is_set())

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
    def test_unlock_waits_for_ui_exit_after_releasing_input(self) -> None:
        stop_event = threading.Event()
        screenlocker._stop_event = stop_event
        ui_exited_event = unittest.mock.MagicMock()
        ui_exited_event.wait.return_value = True
        screenlocker._ui_exited_event = ui_exited_event

        with patch.object(screenlocker.input_blocker, "unblock") as unblock:
            completed = screenlocker.unlock()

        self.assertTrue(stop_event.is_set())
        unblock.assert_called_once()
        ui_exited_event.wait.assert_called_once_with(timeout=5.0)
        self.assertTrue(completed)

    @test_modes("fake")
    def test_run_ui_unblocks_input_when_ui_fails(self) -> None:
        region = ScreenRegion(top=0, left=0, width=100, height=100)
        ready_event = threading.Event()
        failed_event = threading.Event()
        exited_event = threading.Event()

        with (
            patch.object(screenlocker, "_create_windows", return_value=(_FailingRoot(), [])),
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
    def test_run_real_reports_failed_overlay_cleanup(self) -> None:
        output = StringIO()
        errors = StringIO()

        with (
            patch.object(screenlocker, "lock"),
            patch.object(screenlocker, "unlock", side_effect=(False, True)),
            patch(__name__ + "._countdown"),
            redirect_stdout(output),
            redirect_stderr(errors),
        ):
            result = run_real(("lock", "0", "0"))

        self.assertEqual(result, 1)
        self.assertNotIn("State: unlocked", output.getvalue())
        self.assertIn("State: unlock cleanup was not confirmed", errors.getvalue())

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
    def test_app_keeps_photo_image_alive_on_its_label(self) -> None:
        window = _FakeWindow()
        label = _FakeLabel()
        photo = object()
        region = ScreenRegion(top=0, left=0, width=100, height=100)

        with (
            patch.object(screenlocker.ImageTk, "PhotoImage", return_value=photo),
            patch.object(screenlocker.tk, "Label", return_value=label),
        ):
            screenlocker.App(window, Image.new("RGB", (1, 1)), region)

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
    def test_lock_cleans_up_ui_when_input_blocking_fails(self) -> None:
        region = ScreenRegion(top=0, left=0, width=100, height=100)
        ready_event = threading.Event()
        failed_event = threading.Event()
        stop_event = threading.Event()
        exited_event = threading.Event()

        def run_ui() -> None:
            ready_event.set()
            stop_event.wait()
            screenlocker.input_blocker.unblock()
            exited_event.set()

        ui_thread = threading.Thread(target=run_ui)

        def start_ui(
            _: list[ScreenRegion],
        ) -> tuple[threading.Event, threading.Event, threading.Event, threading.Event]:
            screenlocker._stop_event = stop_event
            screenlocker._ui_exited_event = exited_event
            screenlocker._thread = ui_thread
            ui_thread.start()
            return ready_event, failed_event, stop_event, exited_event

        screenlocker._thread = None
        try:
            with (
                patch.object(
                    screenlocker.screen_capture,
                    "get_monitors",
                    return_value=[region],
                ),
                patch.object(screenlocker, "_start_ui", side_effect=start_ui),
                patch.object(
                    screenlocker.input_blocker,
                    "block",
                    side_effect=RuntimeError("Input blocking failed"),
                ),
                patch.object(screenlocker.input_blocker, "unblock") as unblock,
            ):
                with self.assertRaisesRegex(RuntimeError, "Input blocking failed"):
                    screenlocker.lock()

            self.assertTrue(stop_event.is_set())
            self.assertTrue(exited_event.is_set())
            self.assertFalse(ui_thread.is_alive())
            self.assertEqual(unblock.call_count, 2)
        finally:
            stop_event.set()
            ui_thread.join(timeout=1.0)

    @test_modes("real")
    def test_manual_screen_lock_has_cleanup(self) -> None:
        try:
            screenlocker.lock()
        finally:
            screenlocker.unlock()


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
