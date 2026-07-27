# Contract dữ liệu giữa Server và Agent

## TL;DR

Server và Agent chỉ trao đổi message có `message_id`, `kind` và `body`. Network
envelope có target/thời hạn; command cục bộ chỉ có tên allowlist và payload. Agent
luôn trả ack/result; không nhận shell, source code hoặc payload không xác định.

## Hai lớp dữ liệu, hai trách nhiệm

```text
NetworkCommandEnvelope
  -> Agent Network Client kiểm tra message/target/expiry
  -> AgentCommand(name, payload)
  -> CommandDispatcher cục bộ
  -> CommandResult
  -> NetworkResultEnvelope
```

`AgentCommand` là dữ liệu local của dispatcher. Nó chỉ có `command_name` và `payload`,
nên cùng command chạy được từ CLI, unit test hoặc network mà không biết Agent nào là
target hay message đến từ đâu. `NetworkCommandEnvelope` thuộc boundary network và chứa
`message_id`, `target_agent_id`, `expires_at` cùng `AgentCommand` bên trong.

## Envelope chung

Mọi message dùng cùng ý nghĩa dữ liệu:

```text
message_id  # định danh một message
kind        # loại message đã biết
body        # data của loại message đó
```

Khi `kind` là `command`, network body có thêm:

```text
command_id
command_name
target_agent_id
payload
expires_at
```

Chi tiết format serial hóa là quyết định triển khai sau này. Ý nghĩa field phải giữ
ổn định để Server và Agent có thể được build độc lập.

## Message tối thiểu

| Chiều | Kind | Body tối thiểu | Mục đích |
| --- | --- | --- | --- |
| Agent → Server | `hello` | agent identity, Agent version, capability | Agent báo hiện diện. |
| Agent → Server | `heartbeat` | agent identity, health/readiness summary | Server biết Agent còn online. |
| Server → Agent | `command` | command envelope | Yêu cầu một action allowlist. |
| Agent → Server | `command_ack` | command id, accepted/rejected, reason | Agent đã hiểu hoặc từ chối command. |
| Agent → Server | `command_result` | command id, status, detail | Action đã kết thúc hoặc thất bại. |

## Command contract giai đoạn đầu

| Command | Payload | Kết quả Agent |
| --- | --- | --- |
| `status` | rỗng | capability/readiness summary |
| `open_url` | URL HTTP(S) | browser launched hoặc lỗi cục bộ |
| `block_domains` | domain/blocklist đã định nghĩa | applied hoặc permission/validation failure |
| `unblock_domains` | domain/blocklist đã định nghĩa | removed hoặc failure |
| `start_process_guard` | blacklist, whitelist, interval | running/rejected/failed |
| `stop_process_guard` | rỗng | stopped/not running/failed |

`lock_screen`, remote input, capture và shell không thuộc contract đầu.

## Luồng command

```text
1. Teacher gửi yêu cầu đến Server.
2. Server kiểm tra teacher identity và quyền tạo action đó cho Agent đích.
3. Server tạo command_id, chọn target Agent và gửi command.
4. Agent chỉ nhận envelope từ Server đã được Agent tin cậy; Agent Network Client
   validate target và expires_at.
5. Agent Network Client tách `AgentCommand` rồi gửi vào dispatcher local.
6. Dispatcher validate command name/payload, gọi feature qua runtime/platform adapter.
7. Agent trả command_ack và command_result với command_id tương ứng.
8. Server lưu/hiển thị result cho Teacher Console.
```

## Quy tắc chất lượng cơ bản

- `command_id` giúp ghép ack/result đúng command; Agent không chạy mù message lặp.
- `expires_at` ngăn command cũ chạy muộn.
- Mọi lỗi local trả thành result rõ; Server không đoán trạng thái desktop.
- Agent kiểm tra readiness ngay trước action đặc quyền.
- Server kiểm tra teacher identity/quyền trước khi tạo command. Chỉ Server có quyền
  tạo command gửi Agent; Agent không nhận command trực tiếp từ Teacher Console.
- Agent chỉ tin Server đã được nhận diện trong kết nối của Agent; cơ chế xác nhận danh
  tính/kết nối dùng chuẩn platform khi triển khai, không tự thiết kế crypto.

## Policy sau command flow

Khi request-response đã chạy ổn định, thêm `session_policy` versioned để gom nhiều
command thành một phiên học. Chưa thiết kế format policy, offline behavior hoặc retry
trước khi command flow nhỏ nhất có test end-to-end.
