"""Bộ phân loại local.

File path: `src/content_classifier/local/classifier.py`
Input: text gốc và mức kiểm duyệt từ `xlow` đến `xstrict`.
Output: một `ContentCategory` duy nhất.
Nguyên lý: chạy mô hình local với text đã được main API chuẩn hoá, chọn nhãn có
xác suất cao nhất và rơi về `Unknown` khi kết quả không đủ rõ.
"""

from pathlib import Path
from typing import Final

from content_classifier.local.local_model import LocalModel
from content_classifier.tags import ContentCategory
from content_classifier.types import ModerationLevel

_UNKNOWN_MARGIN_THRESHOLDS: Final[dict[ModerationLevel, float]] = {
    "xlow": 0.3,
    "low": 0.167,
    "mid": 0.067,
    "strict": 0.0367,
    "xstrict": 0.0067,
}
MODEL_LABEL_TO_CATEGORY: Final[dict[str, ContentCategory]] = {
    ContentCategory.Pornography.name.lower(): ContentCategory.Pornography,
    ContentCategory.Gore.name.lower(): ContentCategory.Gore,
    ContentCategory.Game.name.lower(): ContentCategory.Game,
    ContentCategory.Unknown.name.lower(): ContentCategory.Unknown,
}


def _map_label_to_category(label: str) -> ContentCategory | None:
    return MODEL_LABEL_TO_CATEGORY.get(label.lower())


class LocalClassifier:
    """Phân loại text và sở hữu model local cần được giải phóng."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        default_path = Path(__file__).resolve().parents[3] / "data" / "models" / "Ritchie.pkl"
        self._model: LocalModel | None = LocalModel(model_path or default_path)

    def classify(
        self,
        text: str,
        moderation_level: ModerationLevel = "mid",
    ) -> ContentCategory:
        """Phân loại text khi chênh lệch dự đoán đạt ngưỡng kiểm duyệt."""

        if self._model is None:
            raise RuntimeError("LocalClassifier is closed")
        predictions = self._model.predict(text, k=2)
        return _select_category(predictions, moderation_level)

    def close(self) -> None:
        """Đóng model local do classifier này sở hữu."""

        if self._model is not None:
            self._model.close()
            self._model = None


def _select_category(
    predictions: dict[str, float],
    moderation_level: ModerationLevel,
) -> ContentCategory:
    """Chọn category từ các dự đoán đã xếp hạng giảm dần."""

    ranked_predictions = list(predictions.items())
    if not ranked_predictions:
        return ContentCategory.Unknown

    top_label, top_probability = ranked_predictions[0]
    if len(ranked_predictions) > 1:
        _, second_probability = ranked_predictions[1]
        margin = top_probability - second_probability
        if margin < _UNKNOWN_MARGIN_THRESHOLDS[moderation_level]:
            return ContentCategory.Unknown

    category = _map_label_to_category(top_label)
    if category is not None:
        return category

    return ContentCategory.Unknown


def local_ai_classifier(
    text: str,
    moderation_level: ModerationLevel = "mid",
) -> ContentCategory:
    """Compatibility API phân loại text bằng một classifier ngắn hạn."""

    classifier = LocalClassifier()
    try:
        return classifier.classify(text, moderation_level)
    finally:
        classifier.close()
