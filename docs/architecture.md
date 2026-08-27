# Kiến trúc SAG Agent

> Đây là kiến trúc **code hiện tại**. Kiến trúc đích có SAG Server, SAG Service và
> SAG Agent nằm tại [`target-architecture.md`](target-architecture.md).
>
> Tài liệu này cần được cập nhật cùng mọi thay đổi về module boundary, protocol,
> factory hoặc lifecycle. Các phần có chữ “tương lai” không phải behavior đã triển
> khai.

## Phạm vi

Repository hiện tại là ứng dụng cục bộ tiền thân của **SAG Agent** trên máy học sinh.
Nó phát hiện platform và cung cấp adapter cho feature desktop có sẵn; CLI
chưa dispatch feature desktop. SAG Server, SAG Service,
Teacher Console và cơ chế giao tiếp giữa chúng chưa tồn tại.

## Chạy Agent

`main.py` hiện chỉ bootstrap runtime. Runtime đã có command dispatch nội bộ qua
allowlist; IPC giữa SAG Service và Agent chưa tồn tại.

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
    +-- process adapter  -> browser_tab, process_guard
    +-- browser adapter  -> browser_tab
    +-- window adapter   -> window_tracker
    +-- hosts adapter    -> web_blocker
    +-- input blocker    -> screen_locker
    +-- key listener     -> keylogger
    `-- input controller factory -> Input resource / caller
```

`agent.runtime` là package public của Runtime:

```text
agent.runtime.AgentRuntime
    |
    +-- FeatureRegistry  -> khai báo tên, loại, factory, điều kiện enable
    +-- FeatureManager   -> tạo và quản lý start/stop/close
    `-- CommandApi       -> route allowlist command tới feature
```

Quy ước public export của feature:

- Service export class có `start()` và `stop()`.
- Resource export class có `close()`.
- Stateless API export function trực tiếp.
- Feature do Runtime quản lý không export global instance.

Muốn thêm feature Runtime-managed, đăng ký `FeatureDefinition` trong
`agent.runtime.feature_registry`; không scan package hoặc dispatch object/method động.

`main.py` hiện chỉ cấu hình logging, tạo runtime và kết thúc process. Runtime tạo một
`PlatformServices` đúng một lần, start feature enabled và shutdown lifecycle qua
`FeatureManager`. Compatibility API public cũ dùng `get_default_platform_services()`
được cache theo process. Command handler dùng cùng runtime đó thay vì tự phát hiện OS.

## Phân lớp và hướng import

```text
main.py -> agent.runtime -> agent.platform -> agent.platform.<os>
feature -> agent.platform_protocols
feature -> agent.platform (chỉ khi không được runtime truyền dependency)
agent.platform.<os> -> standard library / dependency native
```

Không được import theo chiều ngược lại:

```text
agent.platform.<os> -> device_controller hoặc system_monitor  # cấm
agent.platform_protocols -> adapter hoặc feature              # cấm
feature -> agent.platform.linux hoặc agent.platform.windows  # cấm
```

`agent.platform_protocols` gồm các protocol nhỏ theo capability: process, browser, window,
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
| Input | `Input` resource và event chuẩn hóa | adapter evdev/UInput/X11; Win32/SendInput/pynput |
| Screen capture | `ScreenRegion`, downsample, lock | MSS backend đa nền tảng |

Code native process, browser, window, hosts và input nằm tại
`src/agent/platform/linux/` hoặc `src/agent/platform/windows/`. Các package
`device_controller/input_controller` giữ public `Input` resource; `utils/input_blocker`
và `utils/key_listener` giữ compatibility facade cho public API cũ.
Feature trong `device_controller/` và `system_monitor/` không gọi `ps`,
`tasklist`, `taskkill`, `xdotool`, `os.name`, `sys.platform` hay đường dẫn hosts.

## Lifecycle hiện tại và kế hoạch

Runtime hiện sở hữu object `PlatformServices` được tạo trong process. Chưa có runtime
registry cho service/resource và chưa có `AgentRuntime.shutdown()`. Lifecycle đầy đủ
dưới đây là boundary mục tiêu cần hoàn thiện, không phải behavior hiện tại.

Thread dài hạn của `ProcessGuard` và `screen_locker` phải là daemon thread theo
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

`ProcessLookupError` được bỏ qua khi process đã tự thoát. Lỗi scan/kill khác được
ProcessKiller lưu lại và caller gọi `raise_if_failed()` để nhận exception; caller
vẫn không được suy ra kill thành công chỉ từ việc gọi feature.

Core Python và protocol adapter không giả định Ubuntu, Debian, `apt` hoặc `systemd`.
Các dependency native, desktop backend và cách khởi động tiến trình là deployment
concern riêng theo distribution. Điều này không có nghĩa macOS hay mọi hệ POSIX được
hỗ trợ: factory hiện chỉ có adapter Linux và Windows.

## Kiểm thử

Test contract nằm trong các file phẳng `tests/test_process_guard.py`,
`tests/test_input_controller.py`,
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
