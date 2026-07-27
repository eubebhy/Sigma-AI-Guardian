# Đánh giá maintainability

## TL;DR

Platform boundary và fake adapter là nền tốt. Chi phí bảo trì hiện đến từ lifecycle
phân tán, test collection không hoàn chỉnh, docs drift và dependency/tooling không tái
lập. Không có bằng chứng cần rewrite kiến trúc.

## Điểm mạnh đã xác nhận

- Bốn protocol nhỏ trong `src/agent/contracts.py` giữ process/browser/window/hosts
  tách trách nhiệm; adapter không import feature.
- Factory chọn OS một lần, `PlatformServices` immutable và cache singleton có lock.
- Feature chính đã có injection seam; test Agent dùng fake thay vì desktop thật.
- Web blocker chỉ sửa marker section và dùng replace cùng directory.
- Local classifier lazy-load, tránh import model khi chỉ dùng rule/status.

## Coupling và ownership cần theo dõi

| Khu vực | Quan sát | Hậu quả bảo trì | Hành động |
| --- | --- | --- | --- |
| Runtime/feature | Nhiều feature tự lấy process-wide default service | Command layer tương lai có thể tạo lifecycle lẫn lộn | Command handler phải nhận runtime services; không migrate mù. |
| Thread/global state | locker, capture, keylogger, local model, Linux input dùng module/class state | Test order/race/cleanup khó quan sát | Chỉ sửa cùng lifecycle test có chủ đích. |
| Classifier data | Keyword, clean-text phrase, training data và model mapping phân tán | Category mới dễ lệch rule/model/docs | Dùng checklist extension trong knowledge base. |
| Docs/test | README cũ mô tả file/flag không tồn tại; nested tests không discovery | Onboarding sai và regression bị bỏ sót | Đồng bộ trong audit; thêm inventory/CI sau khi gate green. |

## Tài liệu đã được đồng bộ trong audit

- Root README input-controller map được thay bằng layout hiện có và có link ROI reports.
- `src/README.md` bỏ clipboard tracker không tồn tại.
- `scripts/README.md` bỏ script dedupe không tồn tại.
- `tests/README.md` mô tả đúng side effect manual thay vì flag/hosts dev không tồn tại.
- Input docs nêu 17 API chung, bao gồm `get_num_lock_state`.

## Workflow tối thiểu cho maintainer

1. Đọc `AGENTS.md` và `ROI-reports/index.md`.
2. Dùng test fake/targeted trước, sau đó Pyright từng path.
3. Không stage artifact test/log/`__pycache__`; kiểm `git diff --check`.
4. Một thay đổi có side effect phải nêu cleanup, platform condition và test safety.
5. Nếu không xác minh được desktop/permission, ghi rõ giới hạn thay vì claim pass.

## Tự động hóa còn thiếu

Không có CI, branch protection, canonical test runner, packaging metadata hay lockfile.
Đây là P2 vì có thể làm sau khi test matrix được chuẩn hóa; không thêm tool/framework
chỉ để tăng số file cấu hình.
