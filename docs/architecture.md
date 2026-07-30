# Kiến trúc SAG Agent

> Đây là kiến trúc **code hiện tại**. Kiến trúc đích có SAG Server, SAG Service và
> SAG Agent nằm tại [`target-architecture.md`](target-architecture.md).

## Phạm vi

Repository hiện tại là ứng dụng cục bộ tiền thân của **SAG Agent** trên máy học sinh.
Nó phát hiện platform và cung cấp adapter/capability cho feature desktop có sẵn; CLI
hiện chỉ chạy `status`, chưa dispatch feature desktop. SAG Server, SAG Service,
Teacher Console và cơ chế giao tiếp giữa chúng chưa tồn tại.

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
    +-- agent.platform.create_platform_services()
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
    +-- hosts adapter    -> web_blocker
    +-- input blocker    -> screenlocker
    +-- key listener     -> keylogger
    `-- input controller -> compatibility facade / caller
```

`main.py` chỉ parse CLI, tạo runtime và luôn gọi `runtime.shutdown()` khi thoát.
Runtime tạo một `PlatformServices` đúng một lần. Compatibility API public cũ dùng
`get_default_platform_services()` được cache theo process. Khi Agent phát triển
thêm command nội bộ, command handler phải nhận cùng runtime đó thay vì tự phát
hiện OS.

## Phân lớp và hướng import

```text
main.py -> agent.runtime -> agent.platform -> agent.platform.<os>
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

`agent.contracts` gồm các protocol nhỏ theo capability: process, browser, window,
hosts, input blocking, key listener và input controller. Không có một
`PlatformBackend` lớn vì mỗi capability có lifecycle/permission khác nhau; fake
adapter cho test cũng đơn giản hơn.

## Code chung và code riêng platform

| Trách nhiệm | Code chung | Code riêng OS |
| --- | --- | --- |
| Process guard | blacklist, whitelist, daemon thread | `ps` + `SIGKILL`; `tasklist` + `taskkill` |
| Browser | validate URL, ưu tiên browser đang chạy | process spawn/session flags |
| Web block | parse domain, dedupe, marker, atomic write | đường dẫn hosts |
| Window monitor | API title/process chuẩn hóa | PyWinCtl, fallback `xdotool` trên Linux |
| Input | facade public và event chuẩn hóa | adapter evdev/UInput/X11; Win32/SendInput/pynput |
| Screen capture | `ScreenRegion`, downsample, lock | MSS backend đa nền tảng |

Code native process, browser, window, hosts và input nằm tại
`src/agent/platform/linux/` hoặc `src/agent/platform/windows/`. Các package
`device_controler/input_controller`, `utils/input_blocker` và `utils/key_listener`
chỉ giữ compatibility facade cho public API cũ.
Feature trong `device_controler/` và `system_monitor/` không gọi `ps`,
`tasklist`, `taskkill`, `xdotool`, `os.name`, `sys.platform` hay đường dẫn hosts.

## Lifecycle

Runtime sở hữu platform adapter và đóng input blocker, key listener, virtual input
device cùng X11 resource do input controller cache. `ScreenCapture` và overlay của
`screenlocker` vẫn giữ lifecycle feature hiện có; caller phải `unlock()` trước khi
Agent shutdown.

Thread dài hạn của `ProcessKiller` và `screenlocker` phải là daemon thread theo
quy tắc `src/README.md`; command handler tương lai phải gọi `stop()`/`unlock()`
trước khi Agent shutdown. Các hàm này signal và chờ thread của mình kết thúc; hard
kill process không thể chạy Python `finally`.

## Platform và capability

| Platform | Hỗ trợ hiện tại | Điều kiện |
| --- | --- | --- |
| Windows 10/11 | process, browser, hosts, window, input | `tasklist`, `taskkill`, PyWinCtl; admin cho hosts/input block |
| Linux desktop X11/Xorg | process, browser, hosts, window, input | `ps`, `xdotool`, Xorg, evdev/UInput permission; package/init system tùy distribution |
| Wayland | Không hỗ trợ đầy đủ | không quảng bá là tương thích |
| macOS/OS khác | Không hỗ trợ | runtime ném `NotImplementedError`, không fallback Linux |

`status` mô tả adapter có thể chọn. Nó không khẳng định thao tác đặc quyền sẽ
thành công: ghi hosts, grab `/dev/input`, `BlockInput` và desktop Xorg vẫn có thể
thất bại do quyền hoặc session. `ProcessLookupError` được bỏ qua khi process đã tự
thoát. Lỗi scan/kill khác được ProcessKiller lưu lại và caller gọi
`raise_if_failed()` để nhận exception; caller vẫn không được suy ra kill thành công
chỉ từ việc gọi feature.

Core Python và protocol adapter không giả định Ubuntu, Debian, `apt` hoặc `systemd`.
Các dependency native, desktop backend và cách khởi động tiến trình là deployment
concern riêng theo distribution. Điều này không có nghĩa macOS hay mọi hệ POSIX được
hỗ trợ: factory hiện chỉ có adapter Linux và Windows.

## Kiểm thử

Test contract nằm trong các file phẳng `tests/test_agent.py`,
`tests/test_process_guard.py`, `tests/test_input_controller.py`,
`tests/test_key_listener.py` và các feature test
`test_<feature>.py` khác. Safe mode dùng fake adapter, không đọc process thật, không
gọi desktop và không sửa hosts. Xem `tests/README.md` trước khi chạy real mode vì nó
có thể có tác động hệ thống.

Sau khi sửa Python, chạy:

```bash
scripts/clean_pyright_check.sh src
scripts/clean_pyright_check.sh tests
```

Khi sửa script Python, chạy thêm:

```bash
scripts/clean_pyright_check.sh scripts
```
