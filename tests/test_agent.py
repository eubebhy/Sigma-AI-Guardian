"""Kiểm tra runtime và CLI an toàn của SAG Agent.

File path: ``tests/test_agent.py``.
Input: safe mode ``fake``, ``mock`` hoặc ``smoke``; real chỉ nhận ``status``.
Output: pass im lặng, fail in lỗi ngắn.
Nguyên lý: runtime status không cần desktop thật; ``real status`` gọi entry point thật.

Lệnh safe: ``./.pyvenv/bin/python tests/test_agent.py fake smoke``.
Lệnh real chính xác: ``./.pyvenv/bin/python tests/test_agent.py real status``.
Lệnh real chứng minh ``main(['status'])`` tạo runtime hiện tại và in status thực tế,
không gọi feature desktop native.
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import sys
import unittest
from unittest.mock import patch

from test_support import add_source_path, run_module, test_modes


add_source_path()


def run_real(arguments: Sequence[str]) -> int:
    """Chạy status thật có chủ đích, không được gọi bởi safe suite."""

    if tuple(arguments) != ("status",):
        print("Usage: real status", file=sys.stderr)
        return 2
    from main import main

    exit_code = main(["status"])
    print(f"Result: exit code {exit_code}")
    return exit_code


class AgentTests(unittest.TestCase):
    """Runtime phải chọn platform rõ ràng mà không cần desktop thật."""

    @test_modes("fake")
    def test_create_runtime_rejects_unsupported_platform(self) -> None:
        from agent.runtime import create_runtime

        with self.assertRaisesRegex(NotImplementedError, "Unsupported platform"):
            create_runtime(platform_name="darwin")

    @test_modes("fake")
    def test_status_includes_selected_linux_platform(self) -> None:
        from agent.runtime import create_runtime

        runtime = create_runtime(platform_name="linux")

        self.assertIn("Platform: Linux", runtime.status())

    @test_modes("fake")
    def test_status_uses_windows_adapter_without_native_calls(self) -> None:
        from agent.runtime import create_runtime

        runtime = create_runtime(platform_name="windows")

        self.assertIn("Platform: Windows", runtime.status())

    @test_modes("smoke")
    def test_main_status_returns_success(self) -> None:
        from main import main

        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["status"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Sigma AI Guardian Agent", output.getvalue())

    @test_modes("mock")
    def test_run_real_status_invokes_main(self) -> None:
        with patch("main.main", return_value=0) as mocked_main:
            output = StringIO()
            with redirect_stdout(output):
                exit_code = run_real(("status",))

        self.assertEqual(exit_code, 0)
        mocked_main.assert_called_once_with(["status"])
        self.assertEqual(output.getvalue(), "Result: exit code 0\n")

    @test_modes("mock")
    def test_run_real_rejects_non_status_command(self) -> None:
        error = StringIO()
        with patch("main.main") as mocked_main, redirect_stderr(error):
            exit_code = run_real(("start",))

        self.assertEqual(exit_code, 2)
        mocked_main.assert_not_called()
        self.assertEqual(error.getvalue(), "Usage: real status\n")

    @test_modes("mock")
    def test_run_module_parses_real_status_and_calls_runner(self) -> None:
        with patch(__name__ + ".run_real", return_value=0) as mocked_runner:
            exit_code = run_module(sys.modules[__name__], ("real", "status"))

        self.assertEqual(exit_code, 0)
        mocked_runner.assert_called_once_with(("status",))


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
