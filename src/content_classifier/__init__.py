"""API chính của `content_classifier`.

File path: `src/content_classifier/__init__.py`
Input: text gốc và mức kiểm duyệt từ `xlow` đến `xstrict`.
Output: một `ContentCategory` duy nhất.
Nguyên lý: chạy rule-based và local classifier rồi hợp nhất kết quả. Nội dung
cấm là mọi nhãn khác `Unknown`; nếu cả hai engine đều phát hiện nội dung cấm
thì ưu tiên rule-based vì match theo luật thường rõ ràng hơn AI.
"""

from content_classifier.clean_text import clean_text
from content_classifier.local.classifier import LocalClassifier
from content_classifier.types import ContentCategory, ModerationLevel

# TODO: Them he thong timeout
# TODO: Them he thong multi threading noi bo de tang toc
# TODO: Su ly cac truong hop van ban can phan loai qua dai


# Engine APIs
def rule_based_classifier(
    text: str,
    moderation_level: ModerationLevel = "mid",
) -> ContentCategory:
    from content_classifier.rule_based import rule_based_classifier as _classifier

    return _classifier(text, moderation_level)


def local_ai_classifier(
    text: str,
    moderation_level: ModerationLevel = "mid",
) -> ContentCategory:
    from content_classifier.local import local_ai_classifier as _classifier

    return _classifier(text, moderation_level)


# Classifier chính
class _Classifier:
    """Classifier chính, sở hữu local AI và cache runtime."""

    def __init__(self) -> None:
        self._local_ai = LocalClassifier()
        self._cache: list[tuple[str, ModerationLevel, ContentCategory]] = []

    def get_cache(
        self, text: str, moderation_level: ModerationLevel
    ) -> None | ContentCategory:
        for cached_text, cached_level, result in self._cache:
            if cached_text == text and cached_level == moderation_level:
                return result
        return None

    def classify(
        self,
        text: str,
        moderation_level: ModerationLevel = "mid",
    ) -> ContentCategory:

        text = clean_text(text)
        # Tim cache phu hop
        cached_result = self.get_cache(text, moderation_level)
        if cached_result:
            return cached_result

        # Neu tu qua ngan, rac -> Unknown
        if len(text.replace(" ", "")) <= 2:
            return ContentCategory.Unknown

        result = rule_based_classifier(text, moderation_level)

        # Neu van chua bat duoc boi rule_based_classifier va tu du dai thi cho localAI
        if len(text.replace(" ", "")) > 3 and result == ContentCategory.Unknown:
            result = self._local_ai.classify(text, moderation_level)

        if len(self._cache) >= 256:
            self._cache.pop(0)

        self._cache.append((text, moderation_level, result))

        return result

    def close(self) -> None:
        """Đóng local AI và xóa cache runtime."""

        self._local_ai.close()
        self._cache.clear()


classifier = _Classifier()


# Compatibility API
def content_classifier(
    text: str,
    moderation_level: ModerationLevel = "mid",
) -> ContentCategory:
    """Compatibility API gọi object classifier chính."""

    return classifier.classify(text, moderation_level)


# Public exports
__all__ = ["classifier"]
