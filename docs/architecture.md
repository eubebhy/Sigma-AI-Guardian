# Kiến trúc SAG Agent

## Phạm vi

Repository hiện tại là **SAG Agent**: ứng dụng cục bộ chạy trên một máy học sinh.
Agent phát hiện platform và cung cấp adapter/capability cho feature desktop có sẵn;
CLI hiện chỉ chạy `status`, chưa dispatch feature desktop. Repository chưa có Server,
Teacher Console, mạng LAN, protocol từ xa hoặc remote desktop streaming.

## Chạy Agent

Từ thư mục gốc dự án:

```bash
./.pyvenv/bin/python src/main.py status
```

Windows dùng:

```powershell
.\.pyvenv\Scripts\python.exe src\main.py status
```

`status` không thay đổi desktop, input, process hoặc hosts. Nó chỉ in platform
được chọn và những adapter Agent có thể tạo. Quyền truy cập desktop, hosts và
input vẫn được kiểm tra tại thời điểm feature sử dụng chúng.

## Thành phần và luồng chạy

```text
src/main.py
    |
    v
agent.runtime.create_runtime()
    |
    +-- agent.platform.factory.create_platform_services()
    |       |
    |       +-- agent.platform.linux.*
    |       `-- agent.platform.windows.*
    |
    v
AgentRuntime.services
    |
    +-- process adapter  -> browser_tab, process_killer
    +-- browser adapter  -> browser_tab
    +-- window adapter   -> windows_tracker
    `-- hosts adapter    -> web_blocker
```

`main.py` chỉ parse CLI, tạo runtime và luôn gọi `runtime.shutdown()` khi thoát.
Runtime tạo một `PlatformServices` đúng một lần. Compatibility API public cũ dùng
`get_default_platform_services()` được cache theo process. Khi Agent phát triển
thêm command nội bộ, command handler phải nhận cùng runtime đó thay vì tự phát
hiện OS.

## Phân lớp và hướng import

```text
main.py -> agent.runtime -> agent.platform.factory -> agent.platform.<os>
feature -> agent.contracts
feature -> agent.platform (chỉ khi không được runtime truyền dependency)
agent.platform.<os> -> standard library / dependency native
```

Không được import theo chiều ngược lại:

```text
agent.platform.<os> -> device_controler hoặc system_monitor  # cấm
agent.contracts -> adapter hoặc feature                       # cấm
feature -> agent.platform.linux hoặc agent.platform.windows  # cấm
```

`agent.contracts` gồm các protocol nhỏ: `ProcessOperations`,
`BrowserOperations`, `WindowOperations`, `HostsPathOperations`. Không có một
`PlatformBackend` lớn vì process, browser, hosts và window có lifecycle/permission
khác nhau; fake adapter cho test cũng đơn giản hơn.

## Code chung và code riêng platform

| Trách nhiệm | Code chung | Code riêng OS |
| --- | --- | --- |
| Process guard | blacklist, whitelist, daemon thread | `ps` + `SIGKILL`; `tasklist` + `taskkill` |
| Browser | validate URL, ưu tiên browser đang chạy | process spawn/session flags |
| Web block | parse domain, dedupe, marker, atomic write | đường dẫn hosts |
| Window monitor | API title/process chuẩn hóa | PyWinCtl, fallback `xdotool` trên Linux |
| Input | facade public chung | evdev/UInput; Win32/SendInput/pynput |
| Screen capture | `ScreenRegion`, downsample, lock | MSS backend đa nền tảng |

Code native hiện chỉ được phép nằm tại `src/agent/platform/linux/`,
`src/agent/platform/windows/` hoặc backend input hiện có dưới `src/utils/`.
Feature trong `device_controler/` và `system_monitor/` không gọi `ps`,
`tasklist`, `taskkill`, `xdotool`, `os.name`, `sys.platform` hay đường dẫn hosts.

## Lifecycle

Runtime hiện chỉ sở hữu việc chọn platform. `ScreenCapture`, `screenlocker` và
input facade giữ lifecycle hiện có để đợt tái cấu trúc không đổi hành vi desktop.
`main.py` vẫn luôn gọi `runtime.shutdown()` để command Agent tương lai có một nơi
thống nhất để dừng tài nguyên mới.

Thread dài hạn của `ProcessKiller` và `screenlocker` phải là daemon thread theo
quy tắc `src/README.md`; command handler tương lai phải gọi `stop()`/`unlock()`
trước khi Agent shutdown.

## Platform và capability

| Platform | Hỗ trợ hiện tại | Điều kiện |
| --- | --- | --- |
| Windows 10/11 | process, browser, hosts, window, input | `tasklist`, `taskkill`, PyWinCtl; admin cho hosts/input block |
| Ubuntu/Debian GNOME on Xorg | process, browser, hosts, window, input | `ps`, `xdotool`, Xorg, evdev/UInput permission |
| Wayland | Không hỗ trợ đầy đủ | không quảng bá là tương thích |
| macOS/OS khác | Không hỗ trợ | runtime ném `NotImplementedError`, không fallback Linux |

`status` mô tả adapter có thể chọn. Nó không khẳng định thao tác đặc quyền sẽ
thành công: ghi hosts, grab `/dev/input`, `BlockInput` và desktop Xorg vẫn có thể
thất bại do quyền hoặc session. Feature phải trả lỗi thực tế đó cho caller.

## Kiểm thử

Test contract nằm trong `tests/test_agent_runtime.py` và
`tests/test_agent_platform.py`. Chúng dùng fake adapter, không đọc process thật,
không gọi desktop và không sửa hosts. Test integration/manual cũ vẫn ở `tests/`;
xem `tests/README.md` trước khi chạy vì một số test có tác động hệ thống.

Sau khi sửa Python, chạy:

```bash
scripts/clean_pyright_check.sh src
scripts/clean_pyright_check.sh tests
```

Khi sửa script Python, chạy thêm:

```bash
scripts/clean_pyright_check.sh scripts
```

## Hướng phát triển sau SAG Agent

Chỉ sau khi Agent có command lifecycle ổn định mới tạo Server và Teacher Console.
Server tương lai chỉ gửi command đã xác thực đến Agent; nó không được chứa adapter
Windows/Linux hoặc gọi API desktop. Remote desktop và network protocol là dự án
riêng, không thuộc kiến trúc Agent hiện tại.
