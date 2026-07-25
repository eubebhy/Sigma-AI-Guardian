"""Unit test và CLI thủ công cho `clean_text`.

File path: `tests/content_classifier/test_clean_text.py`
Input: cases trong `test_cases/clean_text.json` hoặc chuỗi từ `--text`.
Output: kết quả unittest hoặc chuỗi đã được làm sạch.
Nguyên lý: dùng chung bộ cases để kiểm tra regression tự động; chế độ `--text`
cho phép quan sát nhanh một input tùy ý từ terminal.
"""

import argparse
import json
from pathlib import Path
import sys
from typing import cast
import unittest


TEST_DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIRECTORY.parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
CASE_FILE = TEST_DIRECTORY / "test_cases" / "clean_text.json"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from content_classifier.clean_text import clean_text


def _load_cases() -> list[tuple[str, str]]:
    """Đọc các cặp input/expected từ file JSON riêng của clean text."""

    raw_cases = cast(
        list[dict[str, str]],
        json.loads(CASE_FILE.read_text(encoding="utf-8")),
    )
    return [(case["input"], case["expected"]) for case in raw_cases]


class CleanTextTests(unittest.TestCase):
    """Kiểm tra char-map, ghép từ và fuzzy replacement của `clean_text`."""

    def test_clean_text_cases(self) -> None:
        for input_text, expected in _load_cases():
            with self.subTest(input_text=input_text):
                self.assertEqual(clean_text(input_text), expected)


def _main() -> int:
    parser = argparse.ArgumentParser(description="Test clean_text hoặc clean một chuỗi")
    _ = parser.add_argument("--text", help="Clean một chuỗi thay vì chạy test cases")
    args = parser.parse_args()
    text = cast(str | None, args.text)

    if text is not None:
        print(clean_text(text))
        return 0

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CleanTextTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(_main())
