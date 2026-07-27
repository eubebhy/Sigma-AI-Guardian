# pyright: reportPrivateUsage=false
"""Kiểm tra keylogger nhận event chuẩn từ key listener.

File path: `tests/test_keylogger.py`.
Input: event `(KEY_*, state)` từ listener nền tảng.
Output: unittest xác nhận KeyLogger lưu text đã gõ.
Nguyên lý: gọi trực tiếp callback nội bộ để không cần keyboard thật. Feature này
không ghi dữ liệu bền hay gửi qua mạng.

Lệnh safe: ``./.pyvenv/bin/python tests/test_keylogger.py fake smoke``.
Lệnh real chính xác: ``./.pyvenv/bin/python tests/test_keylogger.py real listen``.
Cảnh báo riêng tư: lệnh real hiển thị mọi text được nhập vào virtual buffer; chỉ chạy
khi có sự đồng ý và không nhập dữ liệu nhạy cảm. Cần backend input được platform hỗ
trợ; trên Linux cần quyền đọc ``/dev/input/event*`` (thường dùng `sudo` hoặc user
thuộc group `input`). Nhấn Ctrl+C để yêu cầu listener dừng, in buffer cuối và thoát
process.
"""

from __future__ import annotations

import contextlib
import io
import sys
import time
import unittest
from collections.abc import Sequence
from unittest.mock import patch

from test_support import add_source_path, run_module, test_modes


add_source_path()

from system_monitor.keylogger import KeyLogger


def _parse_real_arguments(arguments: Sequence[str]) -> bool:
    return tuple(arguments) == ("listen",)


def run_real(arguments: Sequence[str]) -> int:
    """Chạy listener manual và in virtual buffer khi có thay đổi."""

    if not _parse_real_arguments(arguments):
        print("Usage: real listen", file=sys.stderr)
        return 2
    try:
        KeyLogger._buffer.clear()
        KeyLogger._cursor = 0
        KeyLogger._modifiers.clear()
        KeyLogger._caps_lock = False
        KeyLogger._listening = False
        KeyLogger._listener = None
        KeyLogger._listener_error = None
        KeyLogger.start()
        print("Listening for keyboard input. Press Ctrl+C to stop.", flush=True)
        previous_buffer = ""
        while True:
            KeyLogger.raise_if_listener_failed()
            current_buffer = KeyLogger.get_current_buffer()
            if current_buffer != previous_buffer:
                print(f"Virtual buffer: {current_buffer}", flush=True)
                previous_buffer = current_buffer
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"Final virtual buffer: {KeyLogger.get_current_buffer()}", flush=True)
        print("Listening stopped.", flush=True)
        return 0
    except Exception as error:
        print(f"Keylogger listener failed: {error}", file=sys.stderr)
        return 1
    finally:
        KeyLogger.stop()


class KeyLoggerTests(unittest.TestCase):
    """KeyLogger phải hiểu tuple event từ listener."""

    def setUp(self) -> None:
        KeyLogger._buffer.clear()
        KeyLogger._cursor = 0
        KeyLogger._modifiers.clear()

    @test_modes("fake", "smoke")
    def test_collects_letters_and_space(self) -> None:
        KeyLogger._keylogger(("KEY_A", "down"))
        KeyLogger._keylogger(("KEY_B", "down"))
        KeyLogger._keylogger(("KEY_SPACE", "down"))

        self.assertEqual(KeyLogger.get_current_buffer(), "ab ")

    @test_modes("fake", "smoke")
    def test_repeats_printable_keys_for_hold_events(self) -> None:
        KeyLogger._keylogger(("KEY_A", "down"))
        KeyLogger._keylogger(("KEY_A", "hold"))
        KeyLogger._keylogger(("KEY_SPACE", "down"))
        KeyLogger._keylogger(("KEY_SPACE", "hold"))

        self.assertEqual(KeyLogger.get_current_buffer(), "aa  ")

    @test_modes("fake", "smoke")
    def test_collects_punctuation_and_shifted_punctuation(self) -> None:
        KeyLogger._keylogger(("KEY_COMMA", "down"))
        KeyLogger._keylogger(("KEY_SLASH", "down"))
        KeyLogger._keylogger(("KEY_LEFTSHIFT", "down"))
        KeyLogger._keylogger(("KEY_COMMA", "down"))
        KeyLogger._keylogger(("KEY_SLASH", "down"))
        KeyLogger._keylogger(("KEY_LEFTSHIFT", "up"))

        self.assertEqual(KeyLogger.get_current_buffer(), ",/<?")

    @test_modes("fake")
    def test_caps_lock_changes_letter_case_without_changing_digits(self) -> None:
        KeyLogger._keylogger(("KEY_CAPSLOCK", "down"))
        KeyLogger._keylogger(("KEY_A", "down"))
        KeyLogger._keylogger(("KEY_1", "down"))
        KeyLogger._keylogger(("KEY_LEFTSHIFT", "down"))
        KeyLogger._keylogger(("KEY_B", "down"))
        KeyLogger._keylogger(("KEY_LEFTSHIFT", "up"))
        KeyLogger._keylogger(("KEY_CAPSLOCK", "down"))
        KeyLogger._keylogger(("KEY_C", "down"))

        self.assertEqual(KeyLogger.get_current_buffer(), "A1bc")

    @test_modes("fake")
    def test_current_buffer_returns_full_text_without_resetting(self) -> None:
        KeyLogger._keylogger(("KEY_A", "down"))

        self.assertEqual(KeyLogger.get_current_buffer(), "a")
        self.assertEqual(KeyLogger.get_current_buffer(), "a")

    @test_modes("fake")
    def test_buffer_retains_newest_6767_characters_on_overflow(self) -> None:
        KeyLogger._buffer.extend("a" * 6767)
        KeyLogger._cursor = 1
        KeyLogger._keylogger(("KEY_B", "down"))

        self.assertEqual(KeyLogger.get_current_buffer(), "b" + "a" * 6766)
        self.assertEqual(KeyLogger._cursor, 1)
        self.assertLessEqual(KeyLogger._cursor, len(KeyLogger._buffer))

    @test_modes("mock", "smoke")
    def test_system_monitor_listener_forwards_events_to_keylogger(self) -> None:
        events = iter(
            [
                ("KEY_LEFTSHIFT", "down"),
                ("KEY_A", "down"),
                ("KEY_LEFTSHIFT", "up"),
                ("KEY_B", "down"),
            ],
        )

        with patch("system_monitor.keylogger.listen_keys", return_value=events):
            KeyLogger._listening = True
            KeyLogger._listen()

        self.assertEqual(KeyLogger.get_current_buffer(), "Ab")

    @test_modes("mock")
    def test_listener_records_backend_error(self) -> None:
        with patch("system_monitor.keylogger.listen_keys", side_effect=OSError("denied")):
            KeyLogger._listening = True
            KeyLogger._listen()

        self.assertEqual(str(KeyLogger.get_listener_error()), "denied")
        self.assertFalse(KeyLogger._listening)

    @test_modes("mock")
    def test_raise_if_listener_failed_raises_stored_backend_error(self) -> None:
        error = OSError("denied")
        KeyLogger._listener_error = error

        with self.assertRaises(OSError) as context:
            KeyLogger.raise_if_listener_failed()

        self.assertIs(context.exception, error)


class RealKeyLoggerCommandTests(unittest.TestCase):
    def test_parser_accepts_only_listen(self) -> None:
        self.assertTrue(_parse_real_arguments(("listen",)))
        self.assertFalse(_parse_real_arguments(()))
        self.assertFalse(_parse_real_arguments(("listen", "now")))
        self.assertFalse(_parse_real_arguments(("logger",)))

    def test_runner_prints_changed_buffer_and_stops_after_interrupt(self) -> None:
        output = io.StringIO()

        def update_buffer_then_interrupt(_: float) -> None:
            if KeyLogger.get_current_buffer():
                raise KeyboardInterrupt
            KeyLogger._buffer.extend("typed")
            KeyLogger._cursor = len(KeyLogger._buffer)

        KeyLogger._buffer.extend("old")
        KeyLogger._cursor = len(KeyLogger._buffer)
        with (
            patch.object(KeyLogger, "start") as start,
            patch.object(KeyLogger, "stop") as stop,
            patch(__name__ + ".time.sleep", side_effect=update_buffer_then_interrupt),
            contextlib.redirect_stdout(output),
        ):
            result = run_real(("listen",))

        self.assertEqual(result, 0)
        start.assert_called_once_with()
        stop.assert_called_once_with()
        self.assertEqual(output.getvalue().splitlines(), [
            "Listening for keyboard input. Press Ctrl+C to stop.",
            "Virtual buffer: typed",
            "Final virtual buffer: typed",
            "Listening stopped.",
        ])

    def test_runner_reports_listener_error_and_stops(self) -> None:
        output = io.StringIO()
        with (
            patch.object(KeyLogger, "start"),
            patch.object(KeyLogger, "stop") as stop,
            patch.object(
                KeyLogger,
                "raise_if_listener_failed",
                side_effect=OSError("permission denied"),
            ),
            contextlib.redirect_stderr(output),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            result = run_real(("listen",))

        self.assertEqual(result, 1)
        stop.assert_called_once_with()
        self.assertIn("permission denied", output.getvalue())

    def test_runner_rejects_invalid_arguments(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            result = run_real(("other",))

        self.assertEqual(result, 2)
        self.assertEqual(output.getvalue(), "Usage: real listen\n")


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
