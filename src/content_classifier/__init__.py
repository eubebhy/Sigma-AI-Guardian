"""API chính của `content_classifier`.

File path: `src/content_classifier/__init__.py`
Input: text gốc và mức kiểm duyệt từ `xlow` đến `xstrict`.
Output: một `ContentCategory` duy nhất.
Nguyên lý: chạy rule-based và local classifier rồi hợp nhất kết quả. Nội dung
cấm là mọi nhãn khác `Unknown`; nếu cả hai engine đều phát hiện nội dung cấm
thì ưu tiên rule-based vì match theo luật thường rõ ràng hơn AI.
"""

from content_classifier.clean_obfuscate_text import clean_text
from content_classifier.tags import ContentCategory
from content_classifier.types import StrictLevel


def rule_based_classifier(
    text: str,
    strict_level: StrictLevel = "mid",
) -> ContentCategory:
    from content_classifier.rule_based import rule_based_classifier as _classifier

    return _classifier(text, strict_level)


def local_ai_classifier(
    text: str,
    strict_level: StrictLevel = "mid",
) -> ContentCategory:
    from content_classifier.local import local_ai_classifier as _classifier

    return _classifier(text, strict_level)


def content_classifier(
    text: str,
    strict_level: StrictLevel = "mid",
) -> ContentCategory:

    text = clean_text(text)
    letter_count = len(text.replace(" ", ""))
    word_count = len(text.split())

    # Neu qua ngan
    if letter_count <= 2:
        return ContentCategory.Unknown

    # Cum tu ngan dien hinh
    if strict_level in ["xlow"]:
        if letter_count == 3 or word_count <= 3 and letter_count <= 25:
            return rule_based_classifier(text, strict_level)

    # Kiem tra bang rule engine truoc
    # Rule engine co che don gian, neu match kha nang cao dung
    rule_result = rule_based_classifier(text, strict_level)
    if rule_result != ContentCategory.Unknown:
        return rule_result

    # Neu rule engne khong match, gia dinh chuoi phuc tap nen de AI su ly
    local_result = local_ai_classifier(text, strict_level)
    if local_result != ContentCategory.Unknown:
        return local_result

    return ContentCategory.Unknown
