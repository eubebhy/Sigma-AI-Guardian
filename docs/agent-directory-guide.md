# Vai trò thư mục `src/agent/`

## Phạm vi

Tài liệu này mô tả code Agent **đang tồn tại**. Agent hiện tạo adapter Linux/Windows
và chạy command CLI an toàn `status`; chưa có command dispatcher, network transport,
Server hoặc Session Helper.

## Kiến trúc quan trọng nhất

Agent phải dùng **cùng một feature logic** trên Linux và Windows, nhưng mỗi OS gọi API
khác nhau. Kiến trúc tách phần chung và phần riêng OS:

```text
CLI hiện tại / network transport tương lai
                 │
                 ▼
             AgentRuntime
                 │ tạo một lần
                 ▼
          PlatformServices
          ├─ processes
          ├─ browser
          ├─ windows
          └─ hosts
                 │
                 ▼
Feature nghiệp vụ ── dùng contract chung ──► Adapter đúng OS ──► OS API/binary
                                               Linux: ps, /etc/hosts, X11
                                               Windows: tasklist, hosts, Win32
```

### Adapter là gì?

**Adapter** là lớp chuyển một API chung của Agent thành lời gọi riêng của một OS.

Ví dụ feature `ProcessKiller` chỉ cần biết:

```python
processes.list_processes()
processes.kill_process(pid)
```

Nó không cần biết Linux dùng `ps`/signal hay Windows dùng `tasklist`/`taskkill`.
`LinuxProcessOperations` và `WindowsProcessOperations` là hai adapter cùng thực hiện
contract `ProcessOperations`.

Nhờ vậy feature không chứa `if Linux`/`if Windows`, test truyền fake adapter không gọi
OS thật, và thêm OS mới chủ yếu là thêm adapter mới thay vì viết lại feature.

### Vai trò các layer

| Layer | Vai trò trực tiếp |
| --- | --- |
| `src/main.py` | Khởi động process, parse CLI hiện tại và luôn gọi shutdown. |
| `agent/runtime.py` | Trung tâm Agent: tạo và giữ adapter của đúng một OS trong suốt process. Command Core tương lai cũng ở đây. |
| `agent/contracts.py` | Định nghĩa Agent cần gì từ OS, ví dụ list process; không quyết định OS làm bằng cách nào. |
| `agent/platform/` | Chọn và ghép adapter đúng OS thành `PlatformServices`. |
| `agent/platform/linux/`, `windows/` | Code riêng OS, gọi binary/API native. |
| `device_controler/`, `system_monitor/` | Feature nghiệp vụ: block web, process guard, screen lock, capture, monitor input/window. |

`PlatformServices` là một túi dependency gồm adapter `processes`, `browser`, `windows`
và `hosts`. Runtime tạo nó một lần để mọi feature của một Agent process dùng cùng OS
context, thay vì mỗi feature tự phát hiện OS.

## Cây thư mục

```text
src/agent/
├── __init__.py
├── runtime.py
├── capabilities.py
├── contracts.py
└── platform/
    ├── __init__.py
    ├── linux/
    │   ├── __init__.py
    │   ├── browser.py
    │   ├── hosts.py
    │   ├── processes.py
    │   └── windows.py
    └── windows/
        ├── __init__.py
        ├── browser.py
        ├── hosts.py
        ├── processes.py
        └── windows.py
```

## Vai trò từng file

| Đường dẫn | Vai trò | Không được làm |
| --- | --- | --- |
| `agent/__init__.py` | Public API package: export `AgentRuntime` và `create_runtime()`. | Chứa feature hoặc native OS code. |
| `agent/runtime.py` | Tạo runtime cục bộ, giữ một `PlatformServices`, cung cấp `status()` và điểm shutdown. Đây sẽ là nơi sở hữu lifecycle command/feature khi Agent Core được xây. | Tự import adapter Linux/Windows hoặc parse network message. |
| `agent/capabilities.py` | Dataclass mô tả capability adapter đã được chọn; `status()` chỉ dùng dữ liệu này. | Khẳng định permission/desktop thật đã sẵn sàng. |
| `agent/contracts.py` | Protocol nhỏ cho process, browser, window và hosts. Feature phụ thuộc các protocol này để test được bằng fake. | Import feature hay implementation native. |
| `agent/platform/__init__.py` | Public API platform: chuẩn hóa tên OS, lazy-import adapter đúng OS, tạo `PlatformServices` và giữ singleton compatibility process-wide. | Fallback sang OS không hỗ trợ hoặc import feature desktop. |
| `agent/platform/linux/__init__.py` | Ghép Linux adapter và capability thành một `PlatformServices`. | Bị feature import trực tiếp. |
| `agent/platform/linux/browser.py` | Implementation `BrowserOperations` bằng process/browser API Linux. | Chứa policy browser cấp feature. |
| `agent/platform/linux/hosts.py` | Trả đường dẫn `/etc/hosts`. | Tự sửa hosts. |
| `agent/platform/linux/processes.py` | Implementation `ProcessOperations` bằng `ps` và signal Linux. | Chứa blacklist/whitelist policy. |
| `agent/platform/linux/windows.py` | Implementation `WindowOperations` cho desktop Linux/X11. | Quyết định feature nào được theo dõi. |
| `agent/platform/windows/__init__.py` | Ghép Windows adapter và capability thành `PlatformServices`. | Bị feature import trực tiếp. |
| `agent/platform/windows/browser.py` | Implementation `BrowserOperations` bằng Windows process/browser API. | Chứa policy browser cấp feature. |
| `agent/platform/windows/hosts.py` | Trả đường dẫn hosts Windows. | Tự sửa hosts. |
| `agent/platform/windows/processes.py` | Implementation `ProcessOperations` bằng `tasklist`/`taskkill`. | Chứa blacklist/whitelist policy. |
| `agent/platform/windows/windows.py` | Implementation `WindowOperations` cho desktop Windows. | Quyết định feature nào được theo dõi. |

## Flow hiện tại

```text
src/main.py
  → create_runtime()
  → create_platform_services()
  → Linux hoặc Windows adapter
  → AgentRuntime.status()
  → AgentRuntime.shutdown()
```

`status` chỉ đi đến capability adapter. Feature desktop chưa được `main.py` dispatch.
Khi Command Core được thêm, flow sẽ là:

```text
CommandRequest → AgentRuntime.validate/dispatch → Feature → CommandResult
```

CLI, fake network và TCP tương lai chỉ chuyển `CommandRequest`/`CommandResult`; chúng
không tự chọn OS hoặc gọi feature trực tiếp.

## Quy tắc mở rộng

### Thêm command Agent

Command Core tương lai nhận command có cấu trúc tại `AgentRuntime`, validate action và
args, rồi gọi feature qua `PlatformServices`. Transport CLI, fake network hoặc TCP chỉ
chuyển dữ liệu vào/ra; không được gọi feature trực tiếp.

### Thêm OS

1. Thêm implementation cho mọi protocol cần thiết trong `agent/contracts.py`.
2. Tạo package `agent/platform/<os>/` ghép các implementation thành `PlatformServices`.
3. Thêm branch rõ ràng trong `create_platform_services()`.
4. Thêm fake/contract test cho adapter.

Core không hard-code distribution Linux, package manager hay init system. Tuy nhiên
factory hiện chỉ hỗ trợ Linux và Windows; điều này không tự động hỗ trợ macOS hoặc mọi
hệ POSIX.

## Hướng dependency bắt buộc

```text
main.py → agent.runtime → agent.platform → agent.platform.<os>
feature → agent.contracts
```

Không được import ngược từ adapter OS vào feature, hoặc từ `contracts.py` vào adapter.
Xem thêm [`architecture.md`](architecture.md) để biết kiến trúc tổng thể và
[`target-architecture.md`](target-architecture.md) để biết hướng Agent–Server tương lai.
