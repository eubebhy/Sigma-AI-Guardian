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

_CLASSIFIER_CACHE: list[tuple[str, StrictLevel, ContentCategory]] = []


def _get_cached_result(text: str, strict_level: StrictLevel) -> ContentCategory | None:
    """Trả kết quả đã cache của cùng text và mức kiểm duyệt."""
    for cached_text, cached_level, result in _CLASSIFIER_CACHE:
        if cached_text == text and cached_level == strict_level:
            return result
    return None


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

    # Lay cache neu co
    cached_result = _get_cached_result(text, strict_level)
    if cached_result is not None:
        return cached_result

    letter_count = len(text.replace(" ", ""))
    word_count = len(text.split())

    # Neu qua ngan
    if letter_count <= 2:
        return ContentCategory.Unknown

    # Neu co 3 ki tu thi de rule eng
    if letter_count == 3:
        result = rule_based_classifier(text, strict_level)

    # Neu strict_level = xlow thi chap nhan bo qua cac cum tu ngan
    elif strict_level == "xlow" and (word_count <= 3 and letter_count <= 25):
        result = rule_based_classifier(text, strict_level)

    else:
        # Rule engine duoc uu tien; local AI chi xu ly khi rule khong match.
        # Giai thich: Rule engine don gian, neu da match thi thuong dung
        result = rule_based_classifier(text, strict_level)
        if result == ContentCategory.Unknown:
            result = local_ai_classifier(text, strict_level)

    if len(_CLASSIFIER_CACHE) >= 256:
        _CLASSIFIER_CACHE.pop(0)

    _CLASSIFIER_CACHE.append((text, strict_level, result))
    return result
