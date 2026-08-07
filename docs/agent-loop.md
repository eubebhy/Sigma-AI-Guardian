# Thiết kế SAG Agent loop

## Phạm vi

Tài liệu này mô tả SAG Agent chạy cục bộ trên máy học sinh. Agent không chạy SAG
Service và không tự kết nối SAG Server. Agent chỉ cung cấp interface local để SAG
Service tích hợp về sau.

SAG Agent chịu trách nhiệm:

- nhận một công việc từ local interface;
- gọi feature hoặc system monitor tương ứng;
- quản lý lifecycle của object mà Agent đã tạo;
- trả output và trạng thái công việc;
- shutdown sạch toàn bộ resource khi được yêu cầu.

## Bootstrap config

`main.py` chịu trách nhiệm setup config lần đầu. `ConfigObject` chịu trách nhiệm
đọc, validate và áp dụng nội dung config; `main.py` không tự parse TOML.

```text
main.py
  ├── config = ConfigObject()
  ├── config.set_fallback_config("backup.toml")
  ├── config.load("sag_agent_config.toml")
  ├── tạo AgentRuntime và feature objects
  └── start Agent loop
```

Trước khi `load()` hoàn tất, các thuộc tính section của config có giá trị `None`.
Agent không được tạo hoặc start feature trước khi config load thành công hoặc đã
chuyển sang fallback hợp lệ.

Khi file chính không hợp lệ:

```text
load sag_agent_config.toml
  ├── hợp lệ → dùng config chính
  └── lỗi → backup file lỗi → load backup.toml
```

Nếu cả config chính và fallback đều không load được, Agent không start feature và
main kết thúc với lỗi rõ ràng.

## AgentRuntime

`AgentRuntime` là owner của các object mà Agent tạo ra. Runtime không chứa logic
platform cụ thể và không thay thế logic bên trong feature.

```text
AgentRuntime
  ├── ConfigObject
  ├── PlatformServices
  ├── feature objects
  ├── local interface
  ├── execute(request)
  └── shutdown()
```

Feature nhận dependency dùng chung từ Runtime. Feature không tự đọc file config,
không tự chọn platform và không tự tạo lifecycle ngoài phạm vi object của nó.

## Local interface

Local interface là boundary để SAG Service tích hợp về sau. Transport cụ thể chưa
được quyết định; có thể là local socket, named pipe hoặc một cơ chế local khác.

Interface tối thiểu:

```text
receive() -> CommandRequest
send(CommandResult)
close()
```

Interface chỉ encode/decode và chuyển request/response. Nó không gọi trực tiếp
feature, không biết Windows/Linux và không quản lý lifecycle feature.

## Agent loop

Main loop tuần tự nhận công việc từ local interface và giao cho Runtime xử lý.

```text
local interface
  → CommandRequest
  → AgentRuntime.execute(request)
  → feature hoặc system monitor
  → CommandResult
  → local interface
```

Main loop chịu trách nhiệm điều phối, không giữ toàn bộ implementation của feature.
Feature có worker thread riêng khi cần hoạt động dài hạn; Runtime chỉ start, stop,
close hoặc unlock các object mà Runtime sở hữu.

## Lifecycle

```text
setup
  → load config
  → tạo PlatformServices
  → tạo feature objects
  → start feature cần chạy nền
  → start local interface
  → chạy Agent loop

shutdown
  → ngừng nhận request mới
  → stop local interface
  → stop worker feature
  → unlock screen nếu đang lock
  → close screen capture/input/platform resource
  → flush log
```

Shutdown thực hiện theo thứ tự ngược với setup. Mỗi object phải được cleanup bởi
owner đã tạo nó; không dùng hard kill để kết thúc process.

## Config trong runtime

Feature truy cập config thông qua object config được Runtime truyền vào. Feature
không cần biết config nằm ở file nào.

```python
config.web_blocker.block_porn
config.process_guard.blocked_processes
config.screen_lock.message
```

Việc reload config tự động là trách nhiệm của `ConfigObject`. Khi reload hợp lệ,
feature sử dụng giá trị mới ở lần action hoặc scan kế tiếp; không restart toàn bộ
Agent loop chỉ vì config thay đổi.

## Trách nhiệm của main.py

`main.py` chỉ làm bootstrap và giữ vòng đời process:

- tạo và setup `ConfigObject`;
- tạo `AgentRuntime`;
- khởi động Agent loop;
- bắt shutdown signal;
- gọi `runtime.shutdown()`;
- trả exit code phù hợp.

`main.py` không chứa routing feature, logic platform, TOML parsing hoặc side effect
của từng feature.

## Trạng thái triển khai

Repository hiện đã có `AgentRuntime` và `PlatformServices`, nhưng local interface,
`CommandRequest`, `CommandResult` và command dispatch đầy đủ chưa được triển khai.
Tài liệu này là thiết kế cho bước hoàn thiện SAG Agent, không mô tả SAG Service hay
SAG Server.
