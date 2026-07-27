# Technical debt và backlog có bằng chứng

## TL;DR

Không phát hiện P0 trong code được audit. Rủi ro ROI cao nhất còn lại là cleanup
screen locker, lifecycle/process identity, hosts concurrent writer, classifier input
budget và test/automation không làm gate. Không refactor hàng loạt trước khi có test.

## P1

| Vấn đề | Ảnh hưởng/bằng chứng | Nguyên nhân và hậu quả | Xử lý, effort/risk/ROI | Điều kiện và verification |
| --- | --- | --- | --- | --- |
| Screen locker có thể để input bị chặn sau lỗi UI | `src/device_controler/screenlocker/__init__.py:194-260` | UI exception chỉ set event; sau `input_blocker.block()` không có `finally` cleanup. Người dùng có thể mất input khi overlay hỏng. | Ownership cleanup rõ, unblock đúng một lần; M / trung bình / cao. | Fake UI ready rồi `mainloop()` ném; assert unblock và overlay cleanup. |
| Guard process từng chết khi PID biến mất | `ProcessKiller._scan_and_kill()` trước audit | Race list→kill làm daemon thoát, bỏ process sau. | **Đã sửa trong audit:** bỏ qua `ProcessLookupError`/`PermissionError` theo từng PID; S / thấp / cao. | `tests/test_process_killer.py` fake PID đầu biến mất, PID sau vẫn được xử lý. |

## P2

| Vấn đề | Ảnh hưởng/bằng chứng | Nguyên nhân và hậu quả | Xử lý, effort/risk/ROI | Điều kiện và verification |
| --- | --- | --- | --- | --- |
| Stop/start process guard race | `src/device_controler/process_killer/__init__.py:51-68` | `stop()` chỉ đổi boolean; start ngay khi thread cũ sleep có thể return, sau đó thread cũ thoát. | State machine `Event`/lock hoặc join trước restart; S-M / thấp / cao. | Fake clock/Event, stop-start liên tiếp vẫn scan. |
| PID reuse kill nhầm | Process snapshot chỉ `(pid, name)`; Linux/Windows kill theo PID | PID có thể được tái dùng sau scan trước `SIGKILL`/`/F`. | Bổ sung process identity/start time vào contract; M / trung bình / cao. | Fake PID đổi identity trước kill không bị kill. |
| Lost update hosts | `src/device_controler/web_blocker/__init__.py:113-134` | Atomic replace tránh file dở nhưng không khóa read-modify-write liên process. | Cross-platform file lock hoặc serialized owner; M / trung bình / cao. | Hai worker dùng temporary hosts, union domain không mất. |
| Lock Linux báo success không đủ input | `src/utils/input_blocker/linux.py:23-63` | Exception grab bị nuốt; API không trả status. Overlay có thể hiện khi keyboard/mouse chưa bị grab. | Result gồm grabbed/failed, policy rõ; M / trung bình / cao. | Fake một device fail; không báo lock thành công sai. |
| Classifier không có input budget | `clean_text.py`, `rule_based/__init__.py` fuzzy matching | Text/token lớn có thể làm CPU tăng; repository chưa có benchmark tái lập để đặt budget. | Xác định limit bằng golden/adversarial benchmark; M / trung bình / cao. | Regression metric cho normal và adversarial corpus, không tăng false negative ngoài ngưỡng. |
| Test không phải gate | Nested test không được discovery; classifier runner exit 0 khi 10/40 case fail | Regression có thể merge dù test logic đang fail. | Canonical safe test command + CI sau khi chuẩn hóa expected result; M / thấp / cao. | Collection inventory và job fail khi test/gate fail. |

## P3

| Vấn đề | Bằng chứng/hậu quả | Hướng xử lý | Effort / risk / ROI |
| --- | --- | --- | --- |
| Capture recovery leak/race | `screen_capture/capture.py:108-124` thay MSS singleton không đóng cũ | Swap dưới lock, close instance cũ, test retry | M / trung bình / trung bình |
| Window fallback/title collision | Linux PyWinCtl exception không fallback; mapping title làm mất cửa sổ trùng | Contract record có ID, fallback khi exception | M / trung bình / trung bình |
| Windows listener queue không giới hạn | `input_controller/window/listener.py` dùng `Queue()` | Bounded queue/coalesce motion, giữ release event | M / trung bình / trung bình |
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
