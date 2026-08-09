"""Public entry point cho local content classifier.

File path: `src/content_classifier/local/__init__.py`
Input: text gốc được truyền qua `local_ai_classifier`.
Output: `ContentCategory` dự đoán bởi model scikit-learn cục bộ.

Nguyên lý hoạt động: package này chỉ re-export API ổn định từ `classifier.py` để
caller không cần biết file nào đang chứa implementation chi tiết.
"""

from content_classifier.local.classifier import LocalClassifier, local_ai_classifier

__all__ = ["LocalClassifier", "local_ai_classifier"]
