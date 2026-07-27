# Security review

## TL;DR

Không xác nhận remote command surface, `shell=True`, `eval` hoặc `exec` trong runtime
hiện tại. Rủi ro chính là feature local đặc quyền: hosts, process kill, input lock,
key logging và model deserialization. Đây là rủi ro thiết kế/hardening, không phải
kết luận có exploit đang hoạt động.

## Boundary đã xác nhận

- `src/main.py` chỉ hỗ trợ `status`; không có HTTP, IPC, LAN, WebSocket hoặc Server.
- Native command hiện dùng argv-list (`ps`, `tasklist`, `taskkill`, `xdotool`), không
  dùng shell string.
- `open_tab()` chặn URL không bắt đầu HTTP(S), nhưng validation host chi tiết chưa có.
- Web blocker ghi hosts bằng temporary file cùng directory rồi `os.replace()` và chỉ
  sở hữu section có marker.

## Rủi ro và hardening

| Priority | Rủi ro | Evidence | Xử lý trước khi mở command/network boundary |
| --- | --- | --- | --- |
| P1 | UI lỗi sau input block có thể làm người dùng không điều khiển máy | `screenlocker/__init__.py` | Cleanup fail-safe, manual test có recovery rõ. |
| P2 | Hosts writer đồng thời mất policy | `web_blocker/__init__.py` | Serialize read-modify-write, test temp file concurrency. |
| P2 | Process kill có privilege cao và PID reuse | `process_killer`, OS adapters | Identity revalidation, allowlist policy, audit result trước remote command. |
| P2 | Linux lock fail-open nhưng caller không biết | `utils/input_blocker/linux.py` | Structured result và policy fail-open/fail-closed đã quyết định. |
| P3 | `joblib.load()` deserialize pickle | `content_classifier/local/ai_assistant.py` | Chỉ load artifact tin cậy; hash/provenance trước load. |
| P3 | Keylogger/input manual test có dữ liệu nhạy cảm | `system_monitor/keylogger`, input test scripts | Không log/commit dữ liệu thật; manual opt-in và xóa artifact. |
| P3 | Classifier input lớn gây resource exhaustion | Rule/fuzzy classifier | Length/token budget có benchmark. |

## Chính sách bắt buộc trước transport tương lai

1. Command là structured allowlist, không là shell string.
2. Agent kiểm tra local capability, permission và policy; Server tương lai không gọi
   API OS desktop.
3. Có authentication, authorization, audit trail và replay/correlation ID trước action
   đặc quyền. Các thành phần này chưa tồn tại.
4. Không thêm `run_shell`, auto-elevation hay bypass permission.
5. Test tự động không dùng hosts/device/browser/process thật.

## Chưa xác minh

Chưa có penetration test, dependency CVE scan, kiểm chứng ACL hosts Windows,
Administrator/UAC, X11 isolation, model provenance hoặc threat model người dùng. Các
việc này là prerequisite release chứ không được suy ra từ static audit.
