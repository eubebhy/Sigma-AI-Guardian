"""Phân loại nội dung bằng điểm tương đồng với kho từ khóa.

File path: `src/content_classifier/rule_based/__init__.py`
Input: văn bản cần phân loại và mức kiểm duyệt từ `xlow` đến `xstrict`.
Output: category có từ khóa giống văn bản nhất khi điểm đạt ngưỡng tương ứng.
Nguyên lý: tách text đã được main API chuẩn hoá thành từng từ, dùng
`difflib.SequenceMatcher` chấm với kho từ khóa rồi trả category có điểm cao nhất.
"""

from difflib import SequenceMatcher
from pathlib import Path
from typing import Final

from content_classifier.tags import ContentCategory
from content_classifier.types import StrictLevel


_THRESHOLDS: Final[dict[StrictLevel, float]] = {
    "xlow": 0.967,
    "low": 0.9067,
    "mid": 0.8067,
    "strict": 0.7067,
    "xstrict": 0.67,
}


def _similarity(text: str, keyword: str) -> float:
    """Trả độ tương đồng giữa hai chuỗi trong khoảng từ 0.0 đến 1.0."""
    if " " in text:
        raise RuntimeError("Chi duoc truyen tung tu vao ham nay")
    ratio = SequenceMatcher(None, text, keyword).ratio()
    # Phat nhung tu co chieu dai duoi 7 ki tu
    # Vi duoi 7 ki tu rat de gap tu trung nhau
    ratio *= min(len(text), 7) / 7
    return ratio


def _has_keyword(text: str, keyword: str) -> bool:
    """Tra ve true neu keyword xuat hien ben trong text"""
    return keyword in text


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

    words = text.lower().split()

    best_score = 0.0
    best_category = ContentCategory.Unknown

    text = " ".join(set(text.lower().split()))  # Loai bo cac tu trung lap
    # Lay danh sach keywords va category cua chung
    for keywords, category in _KEYWORDS_BY_CATEGORY:
        # Tim xem tu nao trong text khop nhat voi cac keyword
        category_score = max(
            (_similarity(word, keyword) for word in words for keyword in keywords),
            default=0.0,
        )
        for keyword in keywords:
            if _has_keyword(text=text, keyword=keyword):
                category_score += 0.067

        # Neu category hien tai giong nhat thi cap nhat best_category
        if category_score > best_score:
            best_score = category_score
            best_category = category

    # Su ly threshold theo strict_level
    if best_score >= _THRESHOLDS[strict_level]:
        return best_category

    return ContentCategory.Unknown


__all__ = ["rule_based_classifier"]
