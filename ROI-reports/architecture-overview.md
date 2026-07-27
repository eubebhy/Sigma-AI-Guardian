# Kiến trúc hiện tại

## TL;DR

`src/main.py` chỉ chạy command an toàn `status`. `agent/` chọn một bộ adapter
Windows/Linux; feature desktop dùng contract chung hoặc compatibility singleton.
Không có transport, command dispatcher, Server hoặc Teacher Console đang hoạt động.

## Trạng thái đã xác nhận

```text
src/main.py
  -> agent.runtime.create_runtime()
     -> agent.platform.factory.create_platform_services()
        -> agent.platform.linux.* | agent.platform.windows.*
     -> AgentRuntime.status()
```

`main()` luôn gọi `AgentRuntime.shutdown()` trong `finally`. Hiện `shutdown()` chỉ
có docstring vì runtime chưa sở hữu feature sống lâu
([`src/agent/runtime.py`](../src/agent/runtime.py)). Vì vậy `status` chỉ mô tả
adapter có thể tạo, không khẳng định quyền hoặc desktop session sẵn sàng.

## Layer và hướng dependency

| Layer | Trách nhiệm | Không được phụ thuộc vào |
| --- | --- | --- |
| `src/main.py` | Parse CLI và đóng runtime | Feature/adapter riêng OS trực tiếp |
| `src/agent/contracts.py` | Protocol process, browser, window, hosts | Feature và adapter |
| `src/agent/platform/` | Factory, adapter native, `PlatformServices` | `device_controler`, `system_monitor` |
| `src/device_controler/`, `src/system_monitor/` | Nghiệp vụ desktop/monitor | `agent.platform.linux` hoặc `.windows` |
| `src/device_controler/input_controller/` | Gửi input, lifecycle UInput | Feature cấp cao |
| `src/utils/key_listener/` | Lắng nghe input, NumLock | Feature cấp cao |
| `src/utils/` khác | Helper dùng lại | Feature cấp cao |
| `src/content_classifier/` | Chuẩn hóa text, rule và local model | Desktop/Agent runtime |

`PlatformServices` là dataclass immutable gồm bốn protocol nhỏ. Đây là boundary
testable: test truyền fake adapter thay vì gọi `ps`, `taskkill`, browser hay desktop
thật ([`src/agent/platform/factory.py`](../src/agent/platform/factory.py)).

## Luồng dữ liệu và điều khiển

### Platform feature

1. Runtime/factory chọn OS một lần.
2. Feature nhận service injection khi API hỗ trợ, ví dụ
   `ProcessKiller(process_operations=...)` và `open_tab(..., platform_services=...)`.
3. API compatibility không có runtime gọi `get_default_platform_services()`, một
   singleton cache theo process.
4. Adapter thực thi native command/API và trả dữ liệu đã chuẩn hóa.

Điểm cần biết: một số feature hiện vẫn tự lấy compatibility singleton (`browser_tab`,
`process_killer`, `web_blocker`, `windows_tracker`). Đây không phải vòng dependency,
nhưng command layer tương lai phải truyền `AgentRuntime.services` thay vì tạo adapter
mới để giữ một lifecycle rõ ràng.

### Content classifier

`content_classifier(text, strict_level)` gọi `clean_text`, tra FIFO cache 256 phần
tử, chạy rule engine trước và chỉ lazy-load local model khi rule trả `Unknown`
([`src/content_classifier/__init__.py`](../src/content_classifier/__init__.py)).
Nhãn khác `Unknown` được xem là nội dung bị cấm. Cache chưa có lock; chưa dùng nó từ
nhiều thread trong luồng Agent hiện tại.

### Desktop lifecycle

- `ProcessKiller` chạy daemon thread, quét tên process exact-match theo `interval`.
  Chỉ `ProcessLookupError` được tiếp tục; lỗi scan/kill khác dừng daemon, được caller
  đọc lại bằng `raise_if_failed()`.
- `screenlocker.lock()` tạo Tk overlay daemon thread, chờ UI ready rồi block input;
  UI dừng hoặc cleanup lỗi đều raise. `unlock()` signal UI, unblock input và xác nhận
  UI đã thoát.
- `LocalAI` tạo daemon idle monitor, lazy-load model; `close()` signal stop và bỏ
  instance reference, nhưng module-global `_model` vẫn có thể giữ model trong memory.
- Linux input blocker giữ file descriptor evdev trong global registry; descriptor
  phải còn mở thì grab mới còn hiệu lực.

Các lifecycle trên chưa được `AgentRuntime.shutdown()` sở hữu. Không tạo command
feature sống lâu cho tới khi ownership/start/stop được thiết kế và test đầy đủ.

## Invariant quan trọng

- Chỉ Linux và Windows được factory hỗ trợ; OS khác phải fail rõ, không fallback.
- `open_tab()` chỉ chấp nhận URL bắt đầu `http://` hoặc `https://`; URL sai raise
  `ValueError`, mọi lần launch thất bại raise `RuntimeError`.
- `ProcessKiller` so khớp exact process name đã lowercase; whitelist ưu tiên blacklist;
   trước khi kill phải list lại để xác minh PID vẫn có cùng tên normalized. Kiểm tra này
   không chứng minh identity OS bất biến nếu process thay thế dùng cùng tên.
- `ProcessOperations` không được đổi lỗi native thành danh sách rỗng; caller xử lý lỗi
  adapter trực tiếp hoặc gọi `ProcessKiller.raise_if_failed()` cho daemon.
- Web blocker chỉ được thay nội dung giữa `START_MARKER`/`END_MARKER`; marker hỏng là
  lỗi `ValueError`, không được tự sửa file hosts.
- `screen_capture.capture()` chỉ nhận `0.0 < sharpness <= 1.0`.
- `lock()` không được gọi như CLI ngắn hạn: UI/input daemon sẽ chết khi process thoát.

## Điều suy ra và điều chưa xác minh

Thiết kế contract nhỏ và fake adapter cho thấy mục tiêu là tránh coupling OS, nhưng
lý do lịch sử cụ thể không được ghi trong Git được audit. Chưa xác minh trên Windows,
Wayland, quyền `/etc/hosts`, `/dev/uinput`, XInput2, `BlockInput`, `PyWinCtl` và model
`Ritchie.pkl`; xem [platform-differences.md](platform-differences.md).
