"""Kiểm tra tham số CLI của screen locker manual test."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from collections.abc import Callable
from types import ModuleType
from typing import cast
import unittest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_SCRIPT = PROJECT_ROOT / "tests" / "screen_locker.py"


def _load_test_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("screen_locker_test", TEST_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load screen locker test script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScreenLockerCliTests(unittest.TestCase):
    """Đảm bảo CLI dùng khoảng chờ và thời lượng khóa đã thống nhất."""

    def test_defaults_wait_five_seconds_then_lock_for_twenty(self) -> None:
        module = _load_test_script()
        parser_factory = cast(
            Callable[[], argparse.ArgumentParser],
            module.__dict__["_build_parser"],
        )
        parser = parser_factory()
        arguments = parser.parse_args([])

        self.assertTrue(hasattr(arguments, "delay"))
        self.assertEqual(arguments.delay, 5.0)
        self.assertEqual(arguments.seconds, 20.0)


if __name__ == "__main__":
    unittest.main()
