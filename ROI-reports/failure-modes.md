# Failure modes và recovery

## TL;DR

Feature desktop phải fail rõ, cleanup state và có đường recovery. Hiện `status` không
phải readiness check; không dùng nó để kết luận máy có thể lock, ghi hosts hay gửi input.

| Failure mode | Dấu hiệu | Recovery hiện tại | Cải thiện/kiểm chứng cần thiết |
| --- | --- | --- | --- |
| OS không hỗ trợ | `NotImplementedError` từ factory | Dừng rõ, không fallback | Unit test factory; giữ behavior. |
| UI locker không ready/cleanup lỗi | Exception từ `lock()`/`unlock()` | Lifecycle tự signal UI và thử unblock trước khi báo lỗi | Fake timeout/crash/cleanup failure. |
| Evdev không grab/release | Exception từ `block()`/`unblock()` | `block()` rollback; `unblock()` thử release mọi registry entry | Fake grab/release lỗi và kiểm tra mọi cleanup được gọi. |
| PID đã thoát/quyền kill thiếu | `ProcessLookupError`/`PermissionError` | Bỏ qua riêng PID đã thoát; lưu lỗi scan/kill khác để caller nhận qua `raise_if_failed()` | Test PID lỗi + PID sau; thêm health/audit khi có lifecycle. |
| Hosts marker hỏng | `ValueError("Web blocker marker is broken")` | Không tự rewrite hosts | Backup/review file, test broken marker. |
| Ghi hosts permission fail | OS exception | Không có command result chuẩn | Command layer tương lai map thành permission failure. |
| Model file lỗi/không tin cậy | `joblib.load` exception hoặc risk deserialize | Không có manifest/recovery | Verify hash trước load, report actionable error. |
| PyWinCtl/X11 lỗi | Adapter exception/fallback không đầy đủ | Caller có thể fail | Fake error test, readiness report. |

## Sự cố desktop manual

Nếu screen lock có hành vi bất thường, chỉ người có quyền local mới xử lý. Không thêm
code bypass khóa. Trước manual test phải có console/session recovery, hiểu cách
`unlock()` hoạt động, và không chạy trên máy đang có người dùng cần thao tác.

## Log và bằng chứng

Repository không còn subsystem logging runtime. Khi điều tra, ghi command, OS,
permission, stack trace đã loại dữ liệu nhạy cảm, dependency version và bước tái hiện
vào issue/ADR; không commit clipboard, key event hay hosts thật.
