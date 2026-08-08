# SAG Agent roadmap

## Phạm vi hiện tại

Repository này xây dựng **SAG Agent cục bộ** chạy trên Windows/Linux.

Đã có:

- `main.py` làm process entry point.
- `AgentRuntime` tạo platform adapter đúng một lần.
- Platform protocol cho process, browser, window, hosts và input.
- Public feature API chạy độc lập với fake/mock test.
- `Service` protocol với `start()` / `stop()`.
- `Resource` protocol với `close()`.

Chưa có command dispatcher, local API, poll loop hoặc transport mạng.
SAG Server, Teacher Console, LAN, remote desktop và remote shell nằm ngoài scope
hiện tại.

## Nguyên tắc kiến trúc

```text
main.py
  -> AgentRuntime
      -> PlatformServices
          -> Linux/Windows adapter
      -> Service objects
      -> Resource objects
      -> Feature objects
```

- `main.py` chỉ bootstrap process và điều phối runtime.
- `agent/platform_protocols.py` chứa protocol capability của platform.
- `agent/protocols.py` chứa lifecycle protocol chung.
- Feature không tự chọn OS hoặc gọi native command trực tiếp.
- `get_default_platform_services()` chỉ giữ cho compatibility/test độc lập.
- Không tạo registry động, global queue hoặc abstraction chưa có use case.

## Now: hoàn thiện AgentRuntime lifecycle

### Service

Service bắt buộc có:

```python
start() -> None
stop() -> None
```

Tích hợp trước:

- `ProcessGuard`.
- `KeyLogger`.

### Resource

Resource bắt buộc có:

```python
close() -> None
```

Tích hợp các resource có native state hoặc resource dài hạn:

- `ScreenCapture`.
- Input controller.
- Input blocker.
- Key listener backend.
- Screen locker, với `close()` giải phóng trạng thái lock.

### AgentRuntime

Thêm các trách nhiệm:

1. `start_service(service)`: start thành công mới thêm vào danh sách started.
2. `register_resource(resource)`: đăng ký resource do runtime sở hữu.
3. `shutdown()`: stop service theo thứ tự ngược, sau đó close resource theo thứ tự
   ngược.
4. Cleanup tiếp tục khi một component lỗi.
5. Shutdown idempotent.
6. Đăng ký `atexit` làm fallback cho cleanup chính.

**Xong khi:** fake test chứng minh start failure rollback, shutdown reverse order,
cleanup tiếp tục sau lỗi và gọi shutdown nhiều lần an toàn.

## Next: command core

```text
CLI/local API tương lai
  -> CommandRequest
  -> AgentRuntime.execute()
  -> validate action và arguments
  -> feature
  -> CommandResult
```

1. Tạo `CommandRequest` và `CommandResult` tối giản.
2. Thêm allowlist command tĩnh trong `AgentRuntime`.
3. Route command tới feature qua dependency của runtime.
4. Test command hợp lệ, command không tồn tại và lỗi feature.

**Xong khi:** transport không gọi feature trực tiếp và request lỗi không làm chết
Agent runtime.

## Next: local API và poll loop

1. Định nghĩa local API contract `receive()`, `send()` và `close()`.
2. Dùng fake local API trước khi chọn socket, pipe hoặc dependency transport.
3. Implement `runtime.poll_once()` và `runtime.run()`.
4. Poll loop phải có timeout, stop event và không busy-wait.
5. Shutdown phải unblock local API và dừng loop sạch.

## Next: config runtime

1. Bootstrap path theo OS và path override cho dev/test.
2. Load config theo `primary -> last-good -> fallback`.
3. `AgentRuntime.update_config()` áp dụng config mới atomically.
4. Config lỗi không làm mất config đang chạy.
5. Feature nhận section config qua runtime, không đọc TOML global.

## Future: tối ưu WebBlocker

1. Dùng binary AdGuard làm cơ chế block domain chính.
2. Dùng hosts file làm fallback khi AdGuard không khả dụng.
3. Hosts fallback ghi tối đa 9 domain trên một dòng.
4. Cập nhật parser, marker transaction, remove/unblock và count tương ứng.
5. Benchmark kích thước file, thời gian rewrite và độ trễ resolver trên Windows/Linux.

## Future: transport và deployment

Chỉ bắt đầu sau khi command core, lifecycle và local API ổn định:

- Transport LAN được xác thực.
- SAG Server và Teacher Console.
- Windows Service/systemd hoặc deployment tương ứng.
- Reconnect và session management.

Không làm trước khi Agent Core ổn định:

- Remote desktop streaming.
- Remote input qua mạng.
- Remote shell.
- Auto-elevation hoặc bypass quyền OS.

## Verification bắt buộc

Mỗi phase phải có:

- Safe tests dùng fake/mock/temp path.
- Không mở browser, khóa desktop, đọc input thật hoặc ghi hosts thật trong unit test.
- `scripts/clean_pyright_check.sh` cho target Python đã sửa.
- Cập nhật docs khi thay đổi boundary hoặc lifecycle.
