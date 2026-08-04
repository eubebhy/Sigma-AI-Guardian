"""Kiểm tra logger và mở shell manual để ghi log.

File path: ``tests/test_logger.py``.
Input: safe test dùng ``logging.Logger`` trong memory; real nhận ``manual`` rồi nhận
``LEVEL MESSAGE`` từ shell. Output: safe test xác nhận level/message; real ghi vào
``src/logs/app.log``. Nguyên lý: real cấu hình root logger một lần, chạy mẫu log ban
đầu, rồi chuyển từng input hợp lệ thành lời gọi logger tương ứng.

Lệnh safe: ``./.pyvenv/bin/python tests/test_logger.py fake``.
Lệnh real: ``./.pyvenv/bin/python tests/test_logger.py real manual``.
Side effect: real tạo hoặc ghi thêm vào ``src/logs/app.log``. Trong shell, dùng
``help`` để xem lệnh và ``exit`` hoặc ``quit`` để dừng.
"""

from __future__ import annotations

import logging
import sys
import unittest
from collections.abc import Sequence
from pathlib import Path
from unittest.mock import patch

from test_support import add_source_path, run_module, test_modes


add_source_path()

from logger import configure_logging


_COMMAND_METHODS = {
    "debug": "debug",
    "info": "info",
    "warning": "warning",
    "warn": "warning",
    "error": "error",
    "err": "error",
    "critical": "critical",
}


def _manual_test(logger: logging.Logger) -> None:
    for method_name in ("debug", "info", "warning", "error", "critical"):
        method = getattr(logger, method_name)
        method("Some character: !@#$%^&*()_+")
        method("Some numbers: 67 12345 890")


def _print_help() -> None:
    print("Commands:")
    print("  debug MESSAGE")
    print("  info MESSAGE")
    print("  warning MESSAGE  (or: warn MESSAGE)")
    print("  error MESSAGE    (or: err MESSAGE)")
    print("  critical MESSAGE")
    print("  help")
    print("  exit | quit")


def _handle_command(logger: logging.Logger, user_input: str) -> bool:
    command, separator, message = user_input.strip().partition(" ")
    if command in ("exit", "quit"):
        return False
    if command == "help":
        _print_help()
        return True
    method_name = _COMMAND_METHODS.get(command)
    if method_name is None or not separator or not message.strip():
        print("Unknown command. Type help to view available commands.")
        return True
    method = getattr(logger, method_name)
    method(message.strip())
    return True


def _log_file_path() -> Path:
    return Path(__file__).resolve().parent.parent / "src" / "logs" / "app.log"


def run_real(arguments: Sequence[str]) -> int:
    """Chạy shell manual và ghi log vào file thật."""

    if tuple(arguments) != ("manual",):
        print("Usage: real manual", file=sys.stderr)
        return 2
    configure_logging()
    logger = logging.getLogger("manual_logger")
    print(f"Log file: {_log_file_path()}", flush=True)
    _manual_test(logger)
    print("Initial log test completed. Type help to view commands.", flush=True)
    while True:
        try:
            user_input = input("log> ")
        except EOFError:
            print("Manual logger stopped.")
            return 0
        except KeyboardInterrupt:
            print("\nManual logger interrupted.")
            return 130
        if not _handle_command(logger, user_input):
            print("Manual logger stopped.")
            return 0


class LoggerTests(unittest.TestCase):
    @test_modes("fake")
    def test_error_command_logs_message(self) -> None:
        logger = logging.getLogger("test_logger.command")

        with patch.object(logger, "error") as error:
            keeps_running = _handle_command(logger, "err &@$&")

        self.assertTrue(keeps_running)
        error.assert_called_once_with("&@$&")


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
