# Failure modes và recovery

## TL;DR

Feature desktop phải fail rõ, cleanup state và có đường recovery. Hiện `status` không
phải readiness check; không dùng nó để kết luận máy có thể lock, ghi hosts hay gửi input.

| Failure mode | Dấu hiệu | Recovery hiện tại | Cải thiện/kiểm chứng cần thiết |
| --- | --- | --- | --- |
| OS không hỗ trợ | `NotImplementedError` từ factory | Dừng rõ, không fallback | Unit test factory; giữ behavior. |
| UI locker không ready 5s | `RuntimeError` từ `lock()` | Caller phải gọi `unlock()` nếu state chưa rõ | Test timeout/crash cleanup, unblock guaranteed. |
| Evdev không grab | `block()` im lặng tiếp tục device khác | `unblock()` release registry đã grab | Structured result, manual check device coverage. |
| PID đã thoát/quyền kill thiếu | `ProcessLookupError`/`PermissionError` | Audit đã bỏ qua PID lỗi và tiếp tục scan | Test PID lỗi + PID sau; thêm health/audit khi có lifecycle. |
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
