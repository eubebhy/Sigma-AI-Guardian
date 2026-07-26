# pyright: reportPrivateUsage=false
"""Kiểm tra keylogger nhận event chuẩn từ input controller.

File path: `tests/test_keylogger.py`.
Input: event `(KEY_*, state)` từ listener nền tảng.
Output: unittest xác nhận KeyLogger lưu text đã gõ.
Nguyên lý: gọi trực tiếp callback nội bộ để không cần keyboard thật.
"""

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from system_monitor.keylogger import KeyLogger


class KeyLoggerTests(unittest.TestCase):
    """KeyLogger phải hiểu tuple event từ listener."""

    def setUp(self) -> None:
        KeyLogger._buffer.clear()
        KeyLogger._cursor = 0
        KeyLogger._modifiers.clear()

    def test_collects_letters_until_space(self) -> None:
        KeyLogger._keylogger(("KEY_A", "down"))
        KeyLogger._keylogger(("KEY_B", "down"))
        KeyLogger._keylogger(("KEY_SPACE", "down"))

        self.assertEqual(KeyLogger.get_new_typed_words(), "ab")


if __name__ == "__main__":
    unittest.main()
