"""Kiểm tra CLI chung của test runner.

File path: ``tests/test_test_support.py``.
Input: safe mode và các cờ CLI của ``test_support``.
Output: pass im lặng, fail in lỗi ngắn.
Nguyên lý: ``--help`` phải thay thế toàn bộ hành vi ``--info``.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import sys
import unittest

from test_support import run_module, test_modes


class TestSupportTests(unittest.TestCase):
    """CLI chung phải dùng standard help flag."""

    @test_modes("fake")
    def test_help_includes_module_documentation(self) -> None:
        output = StringIO()

        with redirect_stdout(output), self.assertRaises(SystemExit) as error:
            run_module(sys.modules[__name__], ("--help",))

        self.assertEqual(error.exception.code, 0)
        self.assertIn("Kiểm tra CLI chung của test runner.", output.getvalue())

    @test_modes("fake")
    def test_info_is_rejected(self) -> None:
        error = StringIO()

        with redirect_stderr(error), self.assertRaises(SystemExit) as exit_error:
            run_module(sys.modules[__name__], ("--info",))

        self.assertEqual(exit_error.exception.code, 2)
        self.assertIn("safe mode must use", error.getvalue())


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
