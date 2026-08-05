"""Phân loại nội dung bằng điểm tương đồng với kho từ khóa.

File path: `src/content_classifier/rule_based/__init__.py`
Input: văn bản cần phân loại và mức kiểm duyệt từ `xlow` đến `xstrict`.
Output: category có từ khóa giống văn bản nhất khi điểm đạt ngưỡng tương ứng.
Nguyên lý: tách text đã được main API chuẩn hoá thành từng từ, ưu tiên match
chính xác keyword nhiều từ bằng cửa sổ trượt, sau đó dùng `SequenceMatcher` để
chấm fuzzy cho từng từ hoặc từng cụm gần bằng độ dài keyword.
"""

from difflib import SequenceMatcher
from pathlib import Path
from typing import Final

from content_classifier.tags import ContentCategory
from content_classifier.types import StrictLevel


_SIMILARITY_THRESHOLDS: Final[dict[StrictLevel, float]] = {
    "xlow": 0.967,
    "low": 0.9067,
    "mid": 0.8067,
    "strict": 0.7067,
    "xstrict": 0.67,
}


def _similarity(text: str, keyword: str) -> float:
    """Trả độ tương đồng giữa text và keyword trong khoảng từ 0.0 đến 1.0."""
    ratio = SequenceMatcher(None, text, keyword).ratio()
    if text != keyword:
        # Phat nhung tu co chieu dai duoi 7 ki tu
        # Vi duoi 7 ki tu rat de gap tu trung nhau
        ratio *= min(len(text.replace(" ", "")), 7) / 7

    return ratio


def _has_keyword(text: str, keyword: str) -> bool:
    """Tra ve true neu keyword xuat hien ben trong text"""
    return keyword in text


def _unique_words(text: str) -> list[str]:
    """Tách text thành các từ không trùng để giảm số lần so fuzzy từ đơn."""

    words: list[str] = []
    for word in text.split():
        if word not in words:
            words.append(word)
    return words


def _make_windows(words: list[str], window_size: int) -> list[str]:
    """Tạo các cụm liên tiếp có độ dài cố định từ danh sách từ.

    Ví dụ input `i have a mango` với `window_size=2` tạo ra `i have`,
    `have a` và `a mango`. Nếu text ngắn hơn keyword thì so cả text một lần.
    """

    if not words:
        return []
    if len(words) <= window_size:
        return [" ".join(words)]

    windows: list[str] = []
    last_start = len(words) - window_size
    for start in range(0, last_start + 1):
        windows.append(" ".join(words[start : start + window_size]))
    return windows


def _phrase_score(words: list[str], keyword_words: list[str]) -> float:
    """Chấm điểm keyword nhiều từ bằng exact window trước rồi fuzzy window.

    Exact match trả 1.0 để keyword rõ ràng như `rule 34` luôn thắng ngưỡng.
    Fuzzy chỉ thử cửa sổ có độ dài bằng keyword, ngắn hơn một từ hoặc dài hơn
    một từ để tránh so quá rộng và gây false positive.
    """

    keyword = " ".join(keyword_words)
    keyword_size = len(keyword_words)
    exact_windows = _make_windows(words, keyword_size)
    if keyword in exact_windows:
        return 1.0

    best_score = 0.0
    for window_size in (keyword_size, keyword_size - 1, keyword_size + 1):
        if window_size <= 0:
            continue
        penalty = 1.0
        if window_size != keyword_size:
            penalty = 0.9
        for window in _make_windows(words, window_size):
            score = _similarity(window, keyword) * penalty
            if score > best_score:
                best_score = score
    return best_score


def _keyword_score(words: list[str], unique_words: list[str], keyword: str) -> float:
    """Chọn cách chấm điểm phù hợp với keyword một từ hoặc nhiều từ."""

    keyword_words = keyword.split()
    if len(keyword_words) <= 1:
        return max(
            (_similarity(word, keyword) for word in unique_words),
            default=0.0,
        )
    return _phrase_score(words, keyword_words)


def _parse_keywords(file_path: Path) -> tuple[str, ...]:
    """Đọc từ khóa, bỏ dòng trống và phần chú thích bắt đầu bằng `#`."""

    keywords: list[str] = []
    with file_path.open(encoding="utf-8") as keyword_file:
        for line in keyword_file:
            keyword = line.partition("#")[0].strip().lower()
            if keyword:
                keywords.append(keyword)
    return tuple(keywords)


_KEYWORD_DIRECTORY: Final[Path] = Path(__file__).parent / "keywords"
_KEYWORDS_BY_CATEGORY: Final[tuple[tuple[tuple[str, ...], ContentCategory], ...]] = (
    (
        _parse_keywords(_KEYWORD_DIRECTORY / "pornography.txt"),
        ContentCategory.Pornography,
    ),
    (_parse_keywords(_KEYWORD_DIRECTORY / "game.txt"), ContentCategory.Game),
    (_parse_keywords(_KEYWORD_DIRECTORY / "gore.txt"), ContentCategory.Gore),
    (_parse_keywords(_KEYWORD_DIRECTORY / "unknown.txt"), ContentCategory.Unknown),
)


def rule_based_classifier(
    text: str,
    strict_level: StrictLevel,
) -> ContentCategory:
    """Trả category có từ khóa giống văn bản nhất và đạt ngưỡng kiểm duyệt."""

    normalized_text = text.lower()
    words = normalized_text.split()
    unique_words = _unique_words(normalized_text)

    best_score = 0.0
    best_category = ContentCategory.Unknown

    # Lay danh sach keywords va category cua chung
    for keywords, category in _KEYWORDS_BY_CATEGORY:
        # Tim keyword khop nhat; keyword nhieu tu duoc so theo cum lien tiep.
        category_score = max(
            (_keyword_score(words, unique_words, keyword) for keyword in keywords),
            default=0.0,
        )
        for keyword in keywords:
            if _has_keyword(text=normalized_text, keyword=keyword):
                category_score += 0.067

        # Neu category hien tai giong nhat thi cap nhat best_category
        if category_score > best_score:
            best_score = category_score
            best_category = category

    # Su ly threshold theo strict_level
    if best_score >= _SIMILARITY_THRESHOLDS[strict_level]:
        return best_category

    return ContentCategory.Unknown


__all__ = ["rule_based_classifier"]
