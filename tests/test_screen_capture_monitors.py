"""Kiểm tra API lấy danh sách monitor cho screen locker."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from device_controler import screen_capture


class ScreenCaptureMonitorTests(unittest.TestCase):
    """Screen capture phải xuất API monitor công khai."""

    def test_exports_monitor_regions(self) -> None:
        self.assertTrue(hasattr(screen_capture, "get_monitors"))


if __name__ == "__main__":
    unittest.main()
