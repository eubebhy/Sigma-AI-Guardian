# Kế hoạch kiến trúc Agent Runtime

> **Đây là kế hoạch, không phải mô tả code hiện tại.** Các tên như
> `ConfigObject`, `AgentPaths`, `LocalAgentApi`, `CommandRequest` và
> `CommandResult` là API dự kiến hoặc placeholder nếu chưa có file tương ứng.
> Kế hoạch có thể lỗi thời nhanh khi `AgentRuntime`, config, protocol hoặc
> lifecycle thay đổi; phải đối chiếu `src/` và `TODO.md` trước khi triển khai.

## 1. Phạm vi và mục tiêu

Tài liệu này mô tả kiến trúc triển khai tiếp theo của SAG Agent cục bộ. Agent
chạy trên một máy, không chứa SAG Server, SAG Service, LAN transport hoặc remote
control.

Mục tiêu:

- `main.py` là process entry point và public application boundary.
- `AgentRuntime` sở hữu config, platform services, feature và lifecycle.
- Agent có bootstrap path theo OS nhưng vẫn chạy được trong project/dev directory.
- Agent có local API boundary để nhận request và trả response.
- Poll loop không busy-wait và có thể dừng sạch.
- Config có thể được cập nhật an toàn khi Agent đang chạy.
- Mọi resource do Agent tạo ra được cleanup theo thứ tự xác định.

Không nằm trong scope:

- Chọn transport cụ thể cho local API.
- Thiết kế protocol kết nối SAG Server.
- Tự động reload config bằng filesystem watcher.
- Thêm feature desktop mới.

## 2. Boundary tổng thể

```text
OS process
  |
  v
main.py
  |
  +-- bootstrap_paths() -> AgentPaths
  +-- ConfigObject.load()
  +-- AgentRuntime(...)
  +-- runtime.run()
  `-- runtime.shutdown()
          |
          +-- LocalAgentApi
          +-- PlatformServices
          +-- Feature objects
          +-- ConfigObject
          `-- stop_event
```

### `main.py`

`main.py` chỉ điều phối process, không chứa logic feature hoặc OS backend.

Public entry point:

```python
def main(argv: Sequence[str] | None = None) -> int:
    ...
```

Trách nhiệm:

1. Parse command line.
2. Xác định `AgentPaths` theo OS và argument override.
3. Tạo `ConfigObject`, cấu hình fallback path và load config.
4. Tạo `AgentRuntime` bằng các object đã được bootstrap.
5. Đăng ký signal/interrupt handler ở process boundary.
6. Gọi `runtime.run()`.
7. Luôn gọi `runtime.shutdown()` trong `finally`.
8. Chuyển lỗi bootstrap/runtime thành exit code phù hợp.

`main.py` không tự đọc TOML, không tự chọn adapter Linux/Windows và không gọi
feature trực tiếp.

### `AgentRuntime`

`AgentRuntime` là owner duy nhất của resource runtime:

```text
AgentRuntime
  +-- config: ConfigObject
  +-- paths: AgentPaths
  +-- api: LocalAgentApi
  +-- services: PlatformServices
  +-- features
  +-- stop_event
  `-- closed state
```

API tối thiểu dự kiến:

```python
start() -> None
run() -> None
poll_once() -> None
update_config() -> None
shutdown() -> None
```

`AgentRuntime` điều phối request và lifecycle. Logic xử lý của từng feature vẫn
nằm trong feature module tương ứng.

## 3. Bootstrap và path theo OS

Bootstrap path là pure logic: chỉ tạo `Path`, không tạo directory, không ghi file
và không khởi động service.

```text
bootstrap_paths(platform, executable_dir, environment)
  -> AgentPaths
```

`AgentPaths` cần mô tả tối thiểu:

```text
config_path
last_good_config_path
fallback_config_path
data_dir
log_dir
```

Quy tắc ưu tiên:

1. Path truyền rõ ràng qua CLI/API.
2. Path từ environment phù hợp với OS.
3. Path mặc định của OS.
4. Path project/dev chỉ dùng khi chạy development hoặc path OS không tồn tại.

Đề xuất default:

| OS | Config | Data | Log |
| --- | --- | --- | --- |
| Linux | `$XDG_CONFIG_HOME/sigma-ai-guardian/` hoặc `~/.config/sigma-ai-guardian/` | `$XDG_DATA_HOME/sigma-ai-guardian/` hoặc `~/.local/share/sigma-ai-guardian/` | `$XDG_STATE_HOME/sigma-ai-guardian/` hoặc `~/.local/state/sigma-ai-guardian/` |
| Windows | `%APPDATA%\\Sigma-AI-Guardian\\` | `%LOCALAPPDATA%\\Sigma-AI-Guardian\\` | `%LOCALAPPDATA%\\Sigma-AI-Guardian\\logs\\` |

Các path cụ thể phải được gom trong `AgentPaths`; feature không được tự dựng
đường dẫn theo `sys.platform` hoặc environment.

## 4. Config và update runtime

`AgentConfig` là owner hiện tại của việc đọc, validate và lưu last-good config.
Trong kế hoạch tương lai, config object này sẽ được truyền vào runtime. Runtime
chỉ gọi API config, không parse TOML.

```text
startup:
  primary -> last-good -> fallback

update:
  đọc config mới
    -> validate toàn bộ
    -> áp dụng một lần
    -> thông báo feature dùng config mới
```

Config update phải có các tính chất:

- Config không hợp lệ không được áp dụng một phần.
- Config hiện tại tiếp tục hoạt động nếu update thất bại.
- Feature nhận section config qua dependency đã truyền từ runtime.
- Feature áp dụng giá trị mới ở action/scan kế tiếp.
- Update không tự tạo thêm thread hoặc runtime khác.

API update dự kiến:

```python
runtime.update_config(config_path: Path | None = None) -> None
```

Nếu feature cần xử lý thay đổi lifecycle, runtime gọi hook rõ ràng của feature;
không dùng import global hoặc hidden callback.

## 5. Local API và poll loop

Transport chưa được quyết định, nên runtime phụ thuộc protocol nhỏ:

```python
class LocalAgentApi(Protocol):
    def receive(self, timeout: float | None = None) -> CommandRequest | None: ...
    def send(self, result: CommandResult) -> None: ...
    def close(self) -> None: ...
```

API layer chỉ encode/decode và quản lý transport. API layer không biết feature,
platform hoặc config.

Poll loop tuần tự:

```text
while not stop_event.is_set():
    request = api.receive(timeout=poll_interval)
    if request is None:
        continue
    result = runtime.execute(request)
    api.send(result)
```

Nguyên tắc:

- `receive()` phải có timeout hoặc unblock được bởi `close()`.
- Không dùng vòng lặp `while True` không có wait.
- Lỗi một request được chuyển thành `CommandResult` lỗi, không làm chết toàn bộ
  Agent loop.
- Lỗi transport nghiêm trọng làm dừng loop và chuyển sang shutdown.
- `stop_event` là nguồn dừng chung cho loop và worker runtime.

## 6. Lifecycle và shutdown

Startup:

```text
parse args
  -> bootstrap paths
  -> load/validate config
  -> create platform services
  -> create feature objects
  -> start long-running workers
  -> open local API
  -> enter poll loop
```

Shutdown là idempotent và theo thứ tự ngược:

```text
stop accepting new requests
  -> signal stop_event
  -> close/unblock local API
  -> stop feature workers
  -> unlock active screen state
  -> close input/key listener/controller
  -> close remaining platform resources
  -> flush logs
```

Mỗi bước cleanup phải được thử ngay cả khi bước trước lỗi. Runtime gom lỗi cleanup
và trả lỗi sau cùng; không bỏ qua resource còn lại chỉ vì một resource đã fail.

`main.py` gọi `shutdown()` trong `finally`. `AgentRuntime.shutdown()` có lock và
được phép gọi nhiều lần mà không cleanup lặp lại.

## 7. Hướng import và ownership

```text
main.py
  -> agent.bootstrap
  -> config
  -> agent.runtime
  -> agent.platform

agent.runtime
  -> agent.platform_protocols
  -> features
  -> platform services

local_api
  -> agent.protocols
```

Feature không được:

- import config global;
- tự phát hiện OS;
- tự đọc path từ environment;
- tự tạo resource runtime ngoài owner của nó;
- gọi trực tiếp local API transport.

Runtime không được chứa implementation chi tiết của feature hoặc OS backend.

## 8. Kế hoạch triển khai

### Phase 1 — Bootstrap boundary

Files dự kiến:

- `src/agent/bootstrap.py`
- `src/main.py`
- `tests/test_bootstrap.py`

Thực hiện `AgentPaths`, resolver path theo OS và override path. Verify bằng fake
environment và temporary directory, không ghi path hệ thống.

### Phase 2 — Runtime config ownership

Files dự kiến:

- `src/agent/runtime/agent_runtime.py`
- `src/config.py` nếu cần bổ sung API tối thiểu
- test runtime mới phù hợp với lifecycle hiện tại

Truyền config vào runtime/feature, thêm update atomic và test update thất bại không
làm mất config hiện tại.

### Phase 3 — Local API contract

Files dự kiến:

- `src/agent/protocols.py` và `src/agent/platform_protocols.py`
- module local API mới chỉ khi protocol hiện tại chưa có nơi phù hợp
- test local API/loop mới khi các protocol được triển khai

Chỉ thêm contract fake trước; chưa chọn socket, pipe hoặc dependency transport.

### Phase 4 — Poll loop

Files dự kiến:

- `src/agent/runtime/agent_runtime.py`
- `src/main.py`
- test local API/loop mới khi các protocol được triển khai

Implement `start()`, `poll_once()`, `run()` với stop event, timeout và xử lý lỗi
từng request. Verify loop không busy-wait và dừng khi API đóng.

### Phase 5 — Lifecycle integration

Files dự kiến:

- `src/agent/runtime/agent_runtime.py`
- feature modules liên quan khi cần hook lifecycle tối thiểu
- test runtime/lifecycle mới phù hợp với các module thực tế

Tích hợp start/stop/unlock/close theo thứ tự shutdown. Verify shutdown idempotent,
cleanup tiếp tục sau lỗi và không gọi desktop thật trong safe test.

## 9. Tiêu chí hoàn thành

- `main.py` chỉ bootstrap, run và shutdown; không chứa feature routing.
- Path OS được test độc lập và có override cho dev/test.
- Config update invalid không làm thay đổi config đang chạy.
- Poll loop có timeout, xử lý được stop signal và không busy-wait.
- Shutdown gọi được nhiều lần, không leak worker/resource theo contract test.
- Safe tests không mở browser, khóa desktop, đọc input thật, kill process thật hoặc
  ghi hosts thật.
- Chạy pass các test liên quan và Pyright target thay đổi.
