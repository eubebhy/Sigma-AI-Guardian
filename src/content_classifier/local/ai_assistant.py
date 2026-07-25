# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Wrapper lazy-load cho model scikit-learn của local classifier.

File path: `src/content_classifier/local/ai_assistant.py`
Input: đường dẫn model joblib và text cần dự đoán.
Output: dict `{label: probability}` đã sắp theo xác suất giảm dần.

Nguyên lý hoạt động:
- Model chỉ được load khi gọi `predict()` để import package không tốn RAM ngay.
- Model được giữ trong bộ nhớ khi còn dùng và được thread nền unload sau thời gian
  idle ước tính theo kích thước file model.
- Caller phải gọi `close()` nếu tạo object ngắn hạn để dừng thread nền rõ ràng.
"""

import threading
import time
from pathlib import Path
from typing import Any, cast

import joblib  # type: ignore[import-not-found]
from sklearn.pipeline import Pipeline  # type: ignore[import-not-found]

_GB = 1073741824  # 1024 ** 3 bytes
_DEFAULT_IDLE_TIMEOUT_SECONDS = 167.0
_model = None


def _idle_timeout_seconds(model_path: Path) -> float:
    """Estimate how long the model can stay idle before it is unloaded."""
    try:
        size_bytes = model_path.stat().st_size
    except OSError:
        return _DEFAULT_IDLE_TIMEOUT_SECONDS

    if size_bytes <= 0:
        return _DEFAULT_IDLE_TIMEOUT_SECONDS

    timeout = _DEFAULT_IDLE_TIMEOUT_SECONDS * (size_bytes / _GB)
    return max(6.7, timeout)


class LocalAI:
    """Quản lý vòng đời model local và cung cấp API dự đoán xác suất."""

    def __init__(self, model_path: str | Path) -> None:
        """Create a lazy-loading scikit-learn wrapper with idle cleanup."""
        self._model_path: Path = Path(model_path)
        self._model: Any = None
        self._lock: threading.RLock = threading.RLock()
        self._stop_event: threading.Event = threading.Event()
        self._last_used_at: float = time.monotonic()
        self._idle_timeout: float = _idle_timeout_seconds(self._model_path)
        self._monitor_thread: threading.Thread = threading.Thread(
            target=self._monitor_idle_time,
            name="LocalAIIdleMonitor",
            daemon=True,
        )
        self._monitor_thread.start()

    def predict(
        self, text: str, k: int = -1, threshold: float = 0.0
    ) -> dict[str, float]:
        """Load model khi cần và trả về tối đa `k` nhãn đạt `threshold`.

        `k < 0` nghĩa là trả về toàn bộ nhãn model biết. Kết quả giữ thứ tự xác
        suất giảm dần theo output của scikit-learn pipeline.
        """

        model = cast(Pipeline, self._load_model())
        probabilities = model.predict_proba([text])[0]
        labels = cast(Any, model).classes_
        with self._lock:
            self._last_used_at = time.monotonic()

        ranked_predictions = sorted(
            zip(labels, probabilities),
            key=lambda prediction: float(prediction[1]),
            reverse=True,
        )
        selected_predictions = ranked_predictions if k < 0 else ranked_predictions[:k]

        return {
            str(label): float(probability)
            for label, probability in selected_predictions
            if float(probability) >= threshold
        }

    def _load_model(self) -> Any:
        """Load the model once and keep it cached until it is unloaded."""
        global _model

        with self._lock:
            if self._model is not None:
                self._last_used_at = time.monotonic()
                return self._model

            if _model is not None:
                self._model = _model
                return self._model

            self._model = joblib.load(self._model_path)
            _model = self._model
            return self._model

    def _unload_model(self) -> None:
        """Drop the cached model reference."""
        with self._lock:
            self._model = None

    def _monitor_idle_time(self) -> None:
        """Background loop that unloads the model after it stays idle."""
        while not self._stop_event.wait(0.67):
            with self._lock:
                if self._model is None:
                    continue

            idle_seconds = time.monotonic() - self._last_used_at
            if idle_seconds >= self._idle_timeout:
                self._unload_model()

    def close(self) -> None:
        """Stop background monitoring and unload the model."""
        self._stop_event.set()
        self._unload_model()
