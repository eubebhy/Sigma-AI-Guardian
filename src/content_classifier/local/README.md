# `content_classifier.local`

## DESCRIPTION

Package chạy local scikit-learn model qua `joblib`. Public API là
`local_ai_classifier(text, moderation_level="mid")`; input là text và moderation level, output
là `ContentCategory`.

```python
from content_classifier.local import local_ai_classifier

result = local_ai_classifier("example text", "mid")
```

## LIFECYCLE

Model được lazy-load khi API được gọi. `local_model.py` giữ monitor daemon và cung cấp
`close()` để signal, join monitor và bỏ reference instance khi owner đã dùng xong.

## TRUST BOUNDARY

Runtime load `data/models/Ritchie.pkl`. `joblib.load()` có thể deserialize code; chỉ
load artifact từ build/release được tin cậy. Data training nằm tại `data/training/`.
