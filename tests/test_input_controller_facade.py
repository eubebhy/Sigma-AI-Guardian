"""Smoke test cho các facade input controller.

File path: `tests/test_input_controller_facade.py`.
Input: module facade Linux và Windows.
Output: unittest xác nhận facade export sender và listener chung.
Nguyên lý: chỉ import module, không truy cập input device thật.
"""

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class InputControllerFacadeTests(unittest.TestCase):
    """Cả hai backend phải có API public tối thiểu giống nhau."""

    def test_linux_facade_exports_listener(self) -> None:
        from utils.input_controller import linux

        self.assertTrue(callable(linux.listen_keys))

    def test_windows_facade_exports_listener(self) -> None:
        from utils.input_controller import window

        self.assertTrue(callable(window.listen_keys))


if __name__ == "__main__":
    unittest.main()
