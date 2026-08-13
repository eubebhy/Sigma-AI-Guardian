"""Các kiểu dùng chung cho toàn bộ hệ phân loại nội dung.

File path: `src/content_classifier/types.py`
Input: không nhận input runtime; module định nghĩa các kiểu dùng bởi classifier.
Output: `ContentCategory`, `ModerationLevel` và protocol `Classifier`.

Nguyên lý hoạt động: các classifier dùng chung category và moderation level để
trao đổi kết quả nhất quán giữa rule-based, local AI và caller.
"""

from enum import Enum, auto
from typing import Literal, Protocol, TypeAlias


class ContentCategory(Enum):
    """Danh mục nội dung cuối cùng mà hệ thống có thể trả về."""

    Pornography = auto()
    Gore = auto()
    Unknown = auto()
    Game = auto()

ModerationLevel: TypeAlias = Literal["xlow", "low", "mid", "strict", "xstrict"]


class Classifier(Protocol):
    def __call__(
        self,
        text: str,
        moderation_level: ModerationLevel,
    ) -> ContentCategory: ...
