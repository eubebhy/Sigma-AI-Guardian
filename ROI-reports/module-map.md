# Bản đồ module và ownership

## TL;DR

`agent` là platform boundary; `device_controler` thực thi side effect; `system_monitor`
đọc trạng thái; `utils` là compatibility/input; classifier độc lập với desktop.

| Khu vực | Trách nhiệm/API chính | State/lifecycle cần biết |
| --- | --- | --- |
| `src/main.py` | `status` CLI | Tạo/đóng một runtime mỗi lần chạy. |
| `src/agent/` | `AgentRuntime`, capability, protocol, factory | `get_default_platform_services()` cache global có lock. |
| `src/agent/platform/linux/` | `ps`, `SIGKILL`, browser, hosts, PyWinCtl/`xdotool` | Linux window fallback chỉ áp dụng trong adapter. |
| `src/agent/platform/windows/` | `tasklist`, `taskkill`, browser, hosts, PyWinCtl | Cần desktop/permission phù hợp khi gọi feature. |
| `device_controler/browser_tab` | `open_tab()` | Browser ưu tiên executable/process đang có; URL phải HTTP(S). |
| `device_controler/process_killer` | `ProcessKiller` | Daemon thread; blacklist exact-name, whitelist thắng. |
| `device_controler/web_blocker` | `block()`, `unblock()` | Read-modify-replace hosts marker block; mặc định đụng hosts thật. |
| `device_controler/screen_capture` | `ScreenCapture`, `capture()`, `get_monitors()` | MSS singleton global; capture là side effect đọc màn hình. |
| `device_controler/screenlocker` | `lock()`, `unlock()` | Tk/UI thread và input grab global; rủi ro lock desktop. |
| `system_monitor/windows_tracker` | active/open window API | Phụ thuộc `WindowOperations`; map title → process mất title trùng. |
| `system_monitor/keylogger` | `KeyLogger` buffer event | Class-level buffer/listener; coi là dữ liệu nhạy cảm. |
| `utils/input_blocker` | `block()`, `unblock()` | Linux giữ evdev descriptor; Windows dùng `BlockInput`. |
| `utils/input_controller` | 17 API facade input | Linux UInput/Xlib, Windows pydirectinput/pynput; test fake/mock chạy tự động, thiết bị thật không chạy tự động. |
| `content_classifier` | rule/local wrapper | Cache FIFO 256 không lock; model `joblib` lazy-load. |
| `scripts/train_model.py` | train `Ritchie.pkl` | Không phải runtime API; chưa có deterministic/provenance gate. |

## Public và internal API

Public API là tên trong `__all__`, entry point, và các hàm/class được README/module
docstring công bố. Hàm bắt đầu `_` là internal, kể cả khi test hiện gọi private helper
để kiểm tra regression. Không đổi tên, kiểu input/output hoặc side effect public nếu
không có migration và test compatibility.

## Điểm mở rộng an toàn

- Thêm OS: bổ sung implementation cho bốn protocol trong
  [`src/agent/contracts.py`](../src/agent/contracts.py), sau đó thêm factory branch.
- Thêm command Agent: đặt trong `src/agent/`, nhận `AgentRuntime.services`; không
  import adapter OS trực tiếp và không nhận shell string.
- Thêm classifier category: đồng bộ `ContentCategory`, model label mapping, trainer,
  keyword/phrase source và golden tests trong cùng thay đổi.
- Thêm input API: giữ Linux/Windows facade và chữ ký đồng nhất; cập nhật `__all__`,
  docs và facade contract test cùng lúc.

## Khu vực không được thay đổi tùy tiện

`web_blocker` marker format, public input facade, local model label mapping, screen
locker cleanup và contract adapter là compatibility/security boundary. Xem ADR và
[technical-debt.md](technical-debt.md) trước khi sửa.
