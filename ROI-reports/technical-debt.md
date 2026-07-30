# Technical debt và backlog có bằng chứng

## TL;DR

Không phát hiện P0 trong code được audit. Process guard stop/start, screen-locker
cleanup, hosts concurrent writer và classifier test gate đã có coverage. Rủi ro ROI
cao nhất còn lại là process identity, readiness và classifier input budget.

## P2

| Vấn đề | Ảnh hưởng/bằng chứng | Nguyên nhân và hậu quả | Xử lý, effort/risk/ROI | Điều kiện và verification |
| --- | --- | --- | --- | --- |
| PID reuse kill nhầm | Process snapshot chỉ `(pid, name)`; Linux/Windows kill theo PID | Đã list lại ngay trước kill và bỏ qua PID mất/đổi tên; PID có thể vẫn bị tái dùng bởi process cùng tên trước `SIGKILL`/`/F`. | Bổ sung process identity/start time vào contract; M / trung bình / cao. | Fake PID đổi identity trước kill không bị kill. |
| Classifier không có input budget | `clean_text.py`, `rule_based/__init__.py` fuzzy matching | Text/token lớn có thể làm CPU tăng; repository chưa có benchmark tái lập để đặt budget. | Xác định limit bằng golden/adversarial benchmark; M / trung bình / cao. | Regression metric cho normal và adversarial corpus, không tăng false negative ngoài ngưỡng. |
| Capability không phản ánh readiness | `PlatformCapabilities` chỉ mô tả adapter có thể tạo | Command đặc quyền có thể fail vì binary, permission hoặc desktop session. | Tách readiness report tại action boundary; M / thấp / cao. | Fake binary/permission/session, không side effect. |

## P3

| Vấn đề | Bằng chứng/hậu quả | Hướng xử lý | Effort / risk / ROI |
| --- | --- | --- | --- |
| Capture recovery leak/race | `screen_capture/capture.py:108-124` thay MSS singleton không đóng cũ | Swap dưới lock, close instance cũ, test retry | M / trung bình / trung bình |
| Window fallback/title collision | Linux PyWinCtl exception không fallback; mapping title làm mất cửa sổ trùng | Contract record có ID, fallback khi exception | M / trung bình / trung bình |
| Windows listener queue không giới hạn | `utils/key_listener/window.py` dùng `Queue()` | Bounded queue/coalesce motion, giữ release event | M / trung bình / trung bình |
| UInput manager không thread-safe | `linux/utils.py` mutable state không lock | Lock state transition, test barrier | S-M / thấp / trung bình |
| Keylogger mở X11 quá nhiều | `keylogger/__init__.py` kiểm NumLock cho key thường | Chỉ check keypad, handle X11 failure | S / thấp / cao |
| Model artifact trust/reproducibility | `joblib.load`, trainer unsorted/random/direct write | Hash/provenance, deterministic train, atomic artifact write | M / thấp / cao |
| Hosts metadata/durability | `_atomic_write()` chỉ copy mode, không fsync | Chỉ sửa nếu cần policy bảo toàn metadata/durability | M / trung bình / thấp |

## P4 và không làm ngay

- `rapidfuzz` không có import Python tracked nhưng chưa đủ bằng chứng rằng nó không
  phải dependency dự kiến; không tự xóa.
- Không có package/lockfile/CI là debt P2, không phải lý do rewrite packaging.
- Các suppression Pyright ở native/dependency-heavy file cần inventory, không xóa
  hàng loạt vì có thể che limitation stub thực.

## Cách dùng backlog

Mỗi item chỉ bắt đầu khi có owner, expected behavior, fake-based regression test và
scope rõ. Priority không thay thế đánh giá quyền/ảnh hưởng lớp học thực tế.
