# Kiến trúc đích: SAG Server và SAG Agent

## TL;DR

SAG gồm một Server trung tâm trong LAN và nhiều Agent trên máy học sinh. Giáo viên
gửi ý định đến Server; Server gửi command/policy có schema đến Agent; Agent là thành
phần duy nhất được thao tác desktop và hệ điều hành cục bộ.

## Mục tiêu

Giúp giáo viên áp policy lớp học lên máy học sinh bằng dữ liệu đơn giản, có kết quả
rõ ràng, không cho phép thực thi code hoặc shell tùy ý qua mạng.

## Không phải mục tiêu giai đoạn đầu

- Remote shell, gửi Python code, generic command execution.
- Remote desktop streaming, remote input, WebRTC hoặc screen capture liên tục.
- Database lớn, nhiều tenant, phân quyền phức tạp hoặc deployment Internet.
- Để Teacher Console gọi API Windows/Linux trực tiếp.

## Sơ đồ tổng thể

```text
Teacher Console
      |
      v
SAG Server
  - nhận yêu cầu giáo viên
  - giữ Agent online
  - tạo command/policy
  - nhận kết quả
      |
      v
SAG Agent x N
  - kiểm tra message
  - kiểm tra readiness cục bộ
  - chạy command allowlist
  - trả CommandResult
      |
      v
Windows/Linux desktop
```

Server nên là hub duy nhất. Máy giáo viên không giao tiếp peer-to-peer trực tiếp với
từng máy học sinh. Agent chủ động tạo kết nối đến Server để Server không cần biết
chi tiết mạng nội bộ của từng máy Agent.

## Boundary trách nhiệm

| Thành phần | Chịu trách nhiệm | Không chịu trách nhiệm |
| --- | --- | --- |
| Teacher Console | Người giáo viên tạo yêu cầu/policy và xem kết quả | Gọi OS API, giữ connection Agent, quyết định native action |
| SAG Server | Nhận yêu cầu, xác định Agent đích, chuyển command, lưu trạng thái tối thiểu | Gọi hosts, process, browser, input hoặc desktop OS |
| SAG Agent | Kiểm tra command, readiness, action allowlist, cleanup và result | Xác thực giáo viên, quản lý lớp học, tự tạo policy quản trị |
| Platform adapter | Thực thi API Windows/Linux | Network, policy, teacher identity |

## Boundary tin cậy và quyền

Teacher Console gửi yêu cầu nhân danh giáo viên, nhưng chỉ **Server** được xác định
yêu cầu đó có hợp lệ và giáo viên có quyền áp action lên Agent đích hay không. Sau khi
Server chấp nhận, Server tạo command mới cho Agent.

Agent không xác thực giáo viên và không nhận quyền trực tiếp từ Teacher Console. Agent
chỉ tin command đến từ Server đã được Agent nhận diện là Server của mình; sau đó Agent
vẫn kiểm tra command name, payload, expiry và readiness cục bộ. Nhờ vậy, một teacher
request không thể đi thẳng đến desktop máy học sinh.

## Nguyên tắc dữ liệu

Data qua mạng là một ngôn ngữ command nhỏ, không là source code:

```text
command name + payload đã biết -> behavior đã định nghĩa trong Agent
```

Ví dụ `open_url` được Agent map sang `open_tab`; message không thể chứa script để
Agent chạy. Tính mạnh đến từ tổ hợp command allowlist, không đến từ khả năng chạy dữ
liệu tùy ý.

## Trạng thái hiện tại

`src/main.py` mới có `status`; `AgentRuntime` mới chọn platform. Command dispatcher,
Agent network client và Server chưa tồn tại. Xem [`architecture.md`](architecture.md)
để phân biệt code hiện có với kiến trúc đích này.
