# ADR 0004: Phân loại local theo clean text, rule trước, model sau

## TL;DR

Chuẩn hóa text, dùng rule làm fast path và chỉ lazy-load model local khi rule không
phát hiện; chưa đủ chất lượng để tự động khóa desktop.

## Trạng thái

Accepted.

## Bối cảnh và vấn đề

Agent cần phân loại offline nhưng local model tốn thời gian/RAM hơn rule. Text có thể bị
obfuscate và policy strictness khác nhau.

## Quyết định

`content_classifier()` clean text, cache tối đa 256 kết quả, chạy rule-based trước; chỉ
gọi local scikit-learn model nếu rule trả `Unknown`. Nếu cả hai phát hiện nội dung cấm,
rule result được ưu tiên. Model lazy-load trong `LocalAI`.

## Lựa chọn thay thế và trade-off

- Model-only: flexible nhưng cold start/dependency artifact lớn; không chọn.
- Rule-only: nhanh nhưng coverage hạn chế; không chọn.
- Cloud classifier: thêm data/privacy/network dependency; không có implementation.

## Hệ quả

Offline-first và fast-path rõ ràng, nhưng vocabulary/training/model mapping phải đồng
bộ. Cache chưa thread-safe; classifier chưa có budget input hay quality gate đủ tin
cậy để tự động lock desktop.

## Xem xét lại khi

Golden evaluation, model provenance, adversarial latency budget và policy false-positive
được xác nhận. Files: `src/content_classifier/`, `scripts/train_model.py`.
