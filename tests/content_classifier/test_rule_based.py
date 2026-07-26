"""Unit test cho rule-based content classifier.

File path: `tests/content_classifier/test_rule_based.py`
Input: các chuỗi text đã được chuẩn hoá giống đầu vào của rule engine.
Output: kết quả unittest xác nhận category trả về từ rule-based classifier.
Nguyên lý: thêm `src/` vào `sys.path`, gọi trực tiếp rule engine và kiểm tra các
case hồi quy quan trọng để tránh thay đổi matcher làm mất keyword nhiều từ.
"""

from pathlib import Path
import sys
import unittest


TEST_DIRECTORY = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIRECTORY.parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from content_classifier.rule_based import rule_based_classifier
from content_classifier.tags import ContentCategory


class RuleBasedClassifierTests(unittest.TestCase):
    """Kiểm tra các hành vi match keyword quan trọng của rule engine."""

    def test_rule_34_phrase_is_pornography(self) -> None:
        self.assertEqual(
            rule_based_classifier("rule 34", "mid"),
            ContentCategory.Pornography,
        )

if __name__ == "__main__":
    unittest.main()
