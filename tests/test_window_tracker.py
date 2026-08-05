"""Kiểm tra window tracker với adapter fake và quét desktop opt-in.

File path: ``tests/test_window_tracker.py``.
Input: safe suite dùng adapter fake; manual guard nhận ``INTERVAL`` dương tính bằng
giây. Output: guard in startup configuration, trạng thái không có cửa sổ hoặc
``title``, ``process`` và ``category`` của mọi cửa sổ ở mỗi chu kỳ. Nguyên lý:
category khác ``Unknown`` khóa desktop trong 10 giây rồi yêu cầu mở khóa. Guard chỉ
hoàn tất thành công khi screen locker xác nhận cleanup overlay/input.

Lệnh manual chính xác: ``./.pyvenv/bin/python tests/test_window_tracker.py real
guard 1.0``.
Preflight/prerequisites: chạy trong desktop session được platform adapter hỗ trợ và
có quyền tạo overlay khóa màn hình. Side effect: có thể khóa desktop 10 giây khi
phát hiện nội dung không phải ``Unknown``. Ctrl+C hoặc SIGTERM dừng guard, mở khóa
màn hình và khôi phục signal handler trước đó. Nếu cleanup không được xác nhận,
guard in lỗi và trả exit code 1.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import signal
import sys
import threading
import time
import unittest
from collections.abc import Sequence
from types import FrameType
from typing import NoReturn
from unittest.mock import patch

from test_support import add_source_path, run_module, test_modes


add_source_path()

from content_classifier import content_classifier
from content_classifier.tags import ContentCategory
from device_controler import screen_locker as screenlocker
from system_monitor.window_tracker import get_all_open_windows


LOCK_SECONDS = 10.0


class _RealArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _parse_real_arguments(arguments: Sequence[str]) -> argparse.Namespace | None:
    parser = _RealArgumentParser(add_help=False)
    commands = parser.add_subparsers(dest="command", required=True)
    guard = commands.add_parser("guard", add_help=False)
    guard.add_argument("interval", type=float)
    try:
        command = parser.parse_args(arguments)
    except (argparse.ArgumentError, ValueError):
        return None
    if command.interval <= 0.0:
        return None
    return command


def _scan_once() -> tuple[str, str, ContentCategory] | None:
    matched_window: tuple[str, str, ContentCategory] | None = None
    windows = get_all_open_windows()
    if not windows:
        print("Windows: none")
    for title, process_name in windows.items():
        category = content_classifier(f"{process_name} - {title}")
        print(f"title={title!r} process={process_name!r} category={category.name}")
        if matched_window is None and category != ContentCategory.Unknown:
            matched_window = title, process_name, category
    return matched_window


def _sleep_or_stop(stop_event: threading.Event, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while not stop_event.is_set():
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            return
        time.sleep(min(0.2, remaining))


def run_real(arguments: Sequence[str]) -> int:
    """Chạy guard desktop có chủ đích, không được gọi bởi safe suite."""

    command = _parse_real_arguments(arguments)
    if command is None:
        print("Usage: real guard INTERVAL", file=sys.stderr)
        return 2
    stop_event = threading.Event()
    print(f"Guard: interval={command.interval} lock_seconds={LOCK_SECONDS}")

    def _request_stop(_: int, __: FrameType | None) -> None:
        stop_event.set()
        screenlocker.unlock()

    previous_sigint = signal.signal(signal.SIGINT, _request_stop)
    previous_sigterm = signal.signal(signal.SIGTERM, _request_stop)
    result = 0
    try:
        while not stop_event.is_set():
            matched_window = _scan_once()
            if matched_window is not None:
                title, process_name, category = matched_window
                print(
                    f"Blocked: title={title!r} process={process_name!r} "
                    f"category={category.name}"
                )
                screenlocker.lock()
                _sleep_or_stop(stop_event, LOCK_SECONDS)
                if not screenlocker.unlock():
                    print("Unlock failed: UI cleanup was not confirmed", file=sys.stderr)
                    result = 1
                    break
            _sleep_or_stop(stop_event, command.interval)
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        try:
            if not screenlocker.unlock():
                print("Cleanup failed: UI cleanup was not confirmed", file=sys.stderr)
                result = 1
        finally:
            signal.signal(signal.SIGINT, previous_sigint)
            signal.signal(signal.SIGTERM, previous_sigterm)
    return result


class _FakeWindowOperations:
    def get_active_window(self) -> tuple[str, str]:
        return "Lesson", "teacher-tool.exe"

    def get_open_windows(self) -> dict[str, str]:
        return {"Lesson": "teacher-tool.exe"}


class WindowTrackerTests(unittest.TestCase):
    @test_modes("fake", "smoke")
    def test_uses_injected_window_operations(self) -> None:
        windows = get_all_open_windows(_FakeWindowOperations())

        self.assertEqual(windows, {"Lesson": "teacher-tool.exe"})

    @test_modes("real")
    def test_real_window_scan_is_classifiable(self) -> None:
        windows = get_all_open_windows()
        categories = [
            content_classifier(f"{process_name} - {title}")
            for title, process_name in windows.items()
        ]

        self.assertTrue(all(category.name for category in categories))


class RealWindowTrackerCommandTests(unittest.TestCase):
    def test_parse_real_guard_command(self) -> None:
        command = _parse_real_arguments(("guard", "1.5"))

        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.command, "guard")
        self.assertEqual(command.interval, 1.5)

    def test_parse_real_guard_rejects_non_positive_interval(self) -> None:
        self.assertIsNone(_parse_real_arguments(("guard", "0")))

    def test_scan_once_reports_when_no_windows_exist(self) -> None:
        output = StringIO()
        with (
            patch(__name__ + ".get_all_open_windows", return_value={}),
            redirect_stdout(output),
        ):
            result = _scan_once()

        self.assertIsNone(result)
        self.assertEqual(output.getvalue(), "Windows: none\n")

    def test_guard_prints_startup_configuration(self) -> None:
        output = StringIO()

        def stop_after_sleep(stop_event: threading.Event, _: float) -> None:
            stop_event.set()

        with (
            patch(__name__ + ".signal.signal", return_value=None),
            patch(__name__ + "._scan_once", return_value=None),
            patch(__name__ + "._sleep_or_stop", side_effect=stop_after_sleep),
            patch.object(screenlocker, "unlock"),
            redirect_stdout(output),
        ):
            result = run_real(("guard", "1.5"))

        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue(), "Guard: interval=1.5 lock_seconds=10.0\n")

    def test_guard_returns_one_when_unlock_is_not_confirmed(self) -> None:
        errors = StringIO()
        matched_window = ("Game", "game.exe", ContentCategory.Game)

        with (
            patch(__name__ + ".signal.signal", return_value=None),
            patch(__name__ + "._scan_once", return_value=matched_window),
            patch(__name__ + "._sleep_or_stop"),
            patch.object(screenlocker, "lock"),
            patch.object(screenlocker, "unlock", side_effect=(False, True)),
            redirect_stderr(errors),
            redirect_stdout(StringIO()),
        ):
            result = run_real(("guard", "1.5"))

        self.assertEqual(result, 1)
        self.assertIn("Unlock failed: UI cleanup was not confirmed", errors.getvalue())


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
