# Build Server sau Agent: thứ tự học và triển khai

## TL;DR

Không build Server lớn ngay. Hoàn tất local dispatcher của Agent, sau đó build từng
vòng khép kín: Agent online → `status` → command result → Teacher request → session.

## Điều kiện bắt đầu

Agent phải có các phần local sau trước network:

```text
AgentApplication
  -> AgentRuntime
  -> CommandDispatcher
  -> CommandResult
```

Command `status` phải chạy qua dispatcher bằng fake test; dispatcher không được phụ
thuộc network. `AgentCommand(name, payload)` không chứa target Agent, message id hoặc
expiry; Agent Network Client chịu trách nhiệm đổi network envelope thành command local.
Đây là nền để cùng command được gọi từ CLI, test và Server.

## Thứ tự build

### Bước 1: Agent process cục bộ

- Tạo `AgentApplication`, command data, dispatcher và result data.
- Chỉ dispatch `status`.
- **Xong khi:** fake command cho status có accepted/result rõ và shutdown sạch.

### Bước 2: Agent online

- Tạo Server entry point và Agent network client.
- Agent gửi `hello`; Server lưu Agent online trong memory.
- **Xong khi:** Server restart/Agent disconnect không làm Agent thực thi desktop action.

### Bước 3: Round trip `status`

- Teacher request chọn một Agent.
- Server chuyển `status`; Agent trả ack/result; Server hiện result.
- **Xong khi:** mọi message được ghép bằng `command_id`, lỗi Agent vẫn trả result.

### Bước 4: Một action an toàn có kiểm chứng

- Thêm `open_url` hoặc command read-only khác trước.
- Test command handler bằng fake adapter; test network bằng fake/in-memory channel.
- **Xong khi:** Server không import feature desktop hoặc adapter OS.

### Bước 5: Session policy tối thiểu

- Chỉ sau các bước trên mới gom `open_url`, blocklist và process guard thành session.
- Định nghĩa start, stop, expiry và cleanup trước code.
- **Xong khi:** Agent cleanup đúng action thuộc session đó khi stop/failure.

## Khi nào nâng cấp

Chỉ nâng cấp persistence, nhiều lớp học, retry, reconnect policy, dashboard hay
observability khi milestone trước có test ổn định và có nhu cầu thật. Không thêm
remote shell, streaming, remote input hoặc custom cryptography như shortcut.

## Checklist mỗi milestone

1. Đầu vào/đầu ra message đã viết trong contract chưa?
2. Server và Agent có thể test độc lập bằng fake channel chưa?
3. Agent có từ chối command unknown/expired/invalid không?
4. Result có chỉ rõ Agent đã làm gì hoặc tại sao không làm được không?
5. Có cleanup khi Agent shutdown/disconnect/session stop không?
