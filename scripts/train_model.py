"""Train model scikit-learn cho local content classifier.

File path: `scripts/train_model.py`
Input: cac file `.txt` trong `data/training/<category>/`.
Output: file model da train `data/models/Ritchie.pkl`.
Nguyen ly: doc ten category tu thu muc chua file train, train pipeline TF-IDF
ky tu + Logistic Regression, sau do serialize model bang joblib de `LocalModel`
chi load va predict.

Thiet ke ma theo huong sau:
    Chap nhan train lau, ton cpu, may nong de model manh, quet tot.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

from pathlib import Path
from typing import TypeAlias

import joblib  # type: ignore[import-not-found]
from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-not-found]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-not-found]
from sklearn.pipeline import FeatureUnion  # type: ignore[import-not-found]
from sklearn.pipeline import Pipeline  # type: ignore[import-not-found]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DIR = PROJECT_ROOT / "data" / "training"
MODEL_DIR = PROJECT_ROOT / "data" / "models"
DEFAULT_MODEL_NAME = "Ritchie.pkl"
TRAINING_CATEGORY_TO_MODEL_LABEL = {
    "education": "Unknown",
    "game": "Game",
    "gore": "Gore",
    "pornography": "Pornography",
}

TrainingData: TypeAlias = tuple[list[str], list[str]]


def _read_training_data(training_dir: Path) -> TrainingData:
    training_texts: list[str] = []
    training_labels: list[str] = []

    for category_dir in training_dir.iterdir():
        if not category_dir.is_dir():
            continue

        label = TRAINING_CATEGORY_TO_MODEL_LABEL.get(category_dir.name.lower())
        if label is None:
            continue

        for train_file in category_dir.glob("*.txt"):
            with train_file.open("r", encoding="utf-8") as source:
                for raw_line in source:
                    text = raw_line.strip()
                    if not text:
                        continue

                    training_labels.append(label)
                    training_texts.append(text)

    if not training_texts:
        raise RuntimeError(f"No training data found in {training_dir}")

    return training_texts, training_labels


def train_model(
    output_dir: str | Path = MODEL_DIR,
    model_name: str = DEFAULT_MODEL_NAME,
) -> Path:
    """Train scikit-learn model tu data/training va ghi ra file joblib."""
    training_texts, training_labels = _read_training_data(TRAINING_DIR)
    model: Pipeline = Pipeline(
        steps=[
            (
                "vectorizer",
                FeatureUnion(
                    [
                        (
                            "char",
                            TfidfVectorizer(
                                analyzer="char_wb",
                                ngram_range=(4, 7),
                            ),
                        ),
                        (
                            "word",
                            TfidfVectorizer(
                                analyzer="word",
                                ngram_range=(1, 3),
                            ),
                        ),
                    ]
                ),
            ),
            ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000)),
        ]
    )
    _ = model.fit(training_texts, training_labels)

    output_path = Path(output_dir) / model_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _ = joblib.dump(model, output_path)

    return output_path


if __name__ == "__main__":
    print(train_model())
