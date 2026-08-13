# `content_classifier`

## DESCRIPTION

Package phân loại văn bản cục bộ. Input là `str` và `ModerationLevel`; output là một
`ContentCategory`. Main API chuẩn hóa text, dùng rule engine trước, chỉ lazy-load local
model khi rule trả `Unknown`, rồi cache tối đa 256 kết quả.

## PUBLIC API

```python
from content_classifier import content_classifier, rule_based_classifier

result = content_classifier("example text", "mid")
rule_result = rule_based_classifier("example text", "strict")
```

- `content_classifier(text, moderation_level="mid")`: rule trước, local model fallback.
- `rule_based_classifier(text, moderation_level="mid")`: chỉ rule engine.
- `local_ai_classifier(text, moderation_level="mid")`: chỉ local model.

`ModerationLevel` hợp lệ là `xlow`, `low`, `mid`, `strict`, `xstrict`.

## COMPONENTS

- `clean_text.py`: chuẩn hóa text.
- `types.py`: kiểu public.
- `rule_based/`: luật và keyword.
- `local/`: local scikit-learn model qua `joblib`.

Không có cloud classifier trong source hiện tại.
