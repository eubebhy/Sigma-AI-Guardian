from typing import Literal, TypeAlias, Protocol
from content_classifier.tags import ContentCategory

StrictLevel: TypeAlias = Literal["xlow", "low", "mid", "strict", "xstrict"]


class Classifier(Protocol):
    def __call__(self, text: str, strict_level: StrictLevel) -> ContentCategory: ...
