"""Kiểm tra runtime và CLI an toàn của SAG Agent."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class AgentRuntimeTests(unittest.TestCase):
    """Runtime phải chọn platform rõ ràng mà không cần desktop thật."""

    def test_create_runtime_rejects_unsupported_platform(self) -> None:
        from agent.runtime import create_runtime

        with self.assertRaisesRegex(NotImplementedError, "Unsupported platform"):
            create_runtime(platform_name="darwin")

    def test_status_includes_selected_platform(self) -> None:
        from agent.runtime import create_runtime

        runtime = create_runtime(platform_name="linux")

        self.assertIn("Platform: Linux", runtime.status())

    def test_status_uses_windows_adapter_without_native_calls(self) -> None:
        from agent.runtime import create_runtime

        runtime = create_runtime(platform_name="windows")

        self.assertIn("Platform: Windows", runtime.status())

    def test_main_status_returns_success(self) -> None:
        from main import main

        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["status"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Sigma AI Guardian Agent", output.getvalue())


if __name__ == "__main__":
    unittest.main()
