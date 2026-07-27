# Blueprint Server cơ bản

## TL;DR

Server khởi động một application, nhận hai loại message: yêu cầu từ Teacher Console
và trạng thái/kết quả từ Agent. Chỉ `network` tree giao tiếp mạng; service tree xử lý
dữ liệu thuần; Server không chứa platform adapter.

## Entry point Server

Khi chạy, Server phải làm theo thứ tự khái niệm sau:

```text
server entry point
  -> ServerApplication.start()
      -> khởi tạo state/store tối thiểu
      -> khởi tạo Network Gateway
      -> nhận Agent và Teacher Console
      -> route message đến service phù hợp
  -> ServerApplication.shutdown()
      -> dừng nhận message
      -> đóng Agent session
      -> ghi trạng thái cần giữ
```

Entry point không chứa logic classroom, command mapping hay protocol parsing.

## Tree đề xuất

```text
server/
  main.py                    # entry point
  application.py             # start/shutdown và dependency owner
  network/
    gateway.py               # điểm duy nhất nhận/gửi mạng
    agent_channel.py         # Agent connect, disconnect, inbound/outbound
    teacher_channel.py       # Teacher request và response
  services/
    access_service.py        # kiểm tra requester được phép tạo command nào
    agent_registry.py        # Agent online/offline và identity
    command_service.py       # tạo/chuyển command
    policy_service.py        # policy/session đơn giản, khi cần
    result_service.py        # nhận CommandResult
  models/
    messages.py              # message data
    commands.py              # command/policy data
  storage/
    repository.py            # state tối thiểu; có thể in-memory ban đầu
```

Đây là ownership map, không bắt buộc tạo toàn bộ cây trong milestone đầu. Chỉ tạo file
khi nó có trách nhiệm thật.

## Network tree: input và output

| Channel | Input | Xử lý | Output |
| --- | --- | --- | --- |
| `agent_channel` | `hello`, `heartbeat`, `command_ack`, `command_result` | parse và chuyển identity/state đã nhận đến service | accept/reject, command, stop/session update |
| `teacher_channel` | yêu cầu xem Agent, gửi command, tạo session | parse và route request đến service | Agent status, accepted/rejected, command result |

`network/` chỉ parse/serialize/routing message. `agent_registry` mới sở hữu Agent
identity và online/offline state. `network/` cũng không tự quyết command có hợp lệ với
desktop; đó là boundary của Agent.

## Service tree: input và output

| Service | Input | Output |
| --- | --- | --- |
| `access_service` | teacher identity + request | accepted/rejected request trước khi tạo command |
| `agent_registry` | agent identity, connection state | Agent record online/offline |
| `command_service` | teacher request + target Agent | command envelope cho Agent |
| `policy_service` | policy/session request | policy version và command cần gửi |
| `result_service` | `CommandResult` từ Agent | state/audit tối thiểu cho Teacher Console |

## Milestone Server nhỏ nhất

Server đầu tiên chỉ cần:

1. Nhận một Agent đã biết.
2. Hiện Agent online/offline.
3. Gửi command `status` đến một Agent.
4. Nhận và hiển thị result.

Chưa cần lớp học, database thật, UI đẹp, policy dài hạn hay command desktop nguy hiểm.
Tuy vậy, ngay từ flow đầu, Server phải là điểm duy nhất chấp nhận yêu cầu giáo viên và
tạo command cho Agent; Teacher Console không được gửi command trực tiếp.
