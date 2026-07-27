# Mục tiêu hiện tại: SAG Agent đa nền tảng

Repository này hiện chỉ xây dựng **SAG Agent** chạy trên máy học sinh. Agent là
tiến trình cục bộ có entry point, phát hiện Windows/Linux một lần và tạo adapter
platform. CLI hiện chỉ có `status` an toàn; các feature desktop là public API độc
lập, chưa có command dispatcher gọi chúng. Server, Teacher Console, mạng LAN, AI
tool calling mới, UI mới và protocol mạng đều ngoài phạm vi hiện tại.

## Output xác định cuối cùng

1. `src/main.py` là entry point duy nhất của SAG Agent và có lệnh `status` an
   toàn để in platform/capability hiện tại.
2. `src/agent/` là nơi duy nhất giữ runtime, contract, factory và lifecycle của
   Agent.
3. Code riêng Windows/Linux nằm trong `src/agent/platform/linux/` và
   `src/agent/platform/windows/`. Feature không tự kiểm tra OS hoặc gọi binary
   OS trực tiếp.
4. Các public API hiện có (`open_tab`, `ProcessKiller`, `block`, `unblock`,
   `lock`, `unlock`, input facade, classifier) vẫn dùng được.
5. `docs/architecture.md` mô tả đầy đủ entry point, lớp kiến trúc, import,
   lifecycle, capability, giới hạn nền tảng và lộ trình sau Agent.
6. Test tự động dùng fake/mock, không đụng desktop, input device hay hosts thật
   mặc định; Pyright strict đạt cho mã Python đã sửa.

## Công việc được duyệt

### 1. Runtime Agent

- Tạo model capability và contract nhỏ theo từng trách nhiệm: process, browser,
  window và hosts path.
- Tạo factory chọn platform đúng một lần và trả lỗi rõ cho OS không hỗ trợ.
- Tạo lifecycle khởi tạo/dừng Agent; chỉ runtime được quyền tạo adapter OS.
- Không tạo `PlatformBackend` khổng lồ, registry động hay dependency mới.

### 2. Adapter Windows/Linux

- Di chuyển `ps`/`os.kill` và `tasklist`/`taskkill` ra adapter process.
- Di chuyển khác biệt `subprocess.Popen` mở browser ra adapter browser.
- Di chuyển đường dẫn hosts và fallback window tracker (`xdotool`) ra adapter.
- Giữ `utils/input_controller` và `utils/input_blocker` là facade compatibility;
  chỉ sửa để runtime có thể dùng chúng rõ ràng hơn nếu thật sự cần.

### 3. Feature Agent

- `browser_tab`, `process_killer`, `web_blocker`, `windows_tracker` chỉ nhận
  contract/runtime chung và giữ API public cũ.
- `screen_capture` và `screenlocker` giữ nguyên lifecycle hiện có; chỉ sử dụng
  qua entry point/runtime khi feature có command Agent riêng.
- Không thêm command điều khiển mới ngoài `status`; các feature hiện hữu không
  được đổi hành vi chỉ để tái cấu trúc.

### 4. Kiểm chứng và tài liệu

- Thêm test contract/factory/CLI không cần OS desktop thật.
- Giữ hoặc cập nhật test feature liên quan khi dependency injection thay đổi.
- Chạy các script test an toàn, Pyright strict và `git diff --check`.
- Viết tài liệu kiến trúc tại `docs/architecture.md` và kế hoạch thực hiện tại
  `docs/superpowers/plans/`.

## Không làm trong đợt này

- Server, web API, WebSocket, database, LAN discovery, Teacher Console.
- Streaming remote desktop, điều khiển từ xa qua mạng, WebRTC hoặc protocol.
- Hệ thống config/log mới, UI mới, dependency mới hoặc thay đổi classifier.
- Refactor không cần thiết ngoài ranh giới runtime/platform Agent.

## Điều kiện hoàn thành

- Không còn nhánh OS/lệnh `ps`, `tasklist`, `taskkill`, `xdotool` hay đường dẫn
  hosts trong feature đã migration.
- Adapter không import feature; contract không import adapter; feature không
  import backend Windows/Linux trực tiếp.
- Mọi capability thiếu dependency/quyền/desktop session đều có trạng thái hoặc
  lỗi rõ ràng, không fallback sai OS.
- Không thay đổi hành vi public ngoài entry point `status` mới.

---

# Hướng phát triển tiếp: SAG Agent vận hành được

Blueprint kiến trúc đích để build dần Server nằm tại
[`docs/index.md`](docs/index.md). Các tài liệu này mô tả boundary và data flow, không
chọn framework, library hoặc kỹ thuật networking cụ thể.

## SAG Agent thực sự là gì?

SAG Agent là tiến trình cài trên **mỗi máy học sinh**. Nó là lớp duy nhất được
phép thao tác với desktop và hệ điều hành của máy đó: khóa màn hình, mở URL,
chặn domain, quản lý process, đọc trạng thái desktop và sau này gửi frame màn
hình. Agent không phải Server, không hiển thị giao diện giáo viên, không quản lý
lớp học và không tự đưa ra quyết định quản trị.

Khi dự án đầy đủ, Server sẽ xác thực lệnh giáo viên rồi gửi command đã định nghĩa
đến Agent. Agent kiểm tra capability/quyền/policy cục bộ, thực thi feature và trả
`CommandResult`. Server không được gọi Win32, evdev, hosts hay API desktop.

```text
Teacher Console (tương lai)
        -> SAG Server (tương lai: auth, classroom, audit, relay)
        -> SAG Agent (repo hiện tại: capability và OS action)
        -> Windows/Linux desktop
```

Trong giai đoạn hiện tại chưa có network. Cần xây dựng **command dispatcher chạy
trong cùng process Agent** trước; transport LAN sau này chỉ là một caller khác của
dispatcher đó.

## Kiến trúc đích của Agent

```text
main.py
  -> AgentApplication                 # start/shutdown của một Agent process
      -> AgentRuntime                 # platform services đã chọn một lần
      -> CommandDispatcher            # allowlist command và kiểm tra capability
          -> Feature service          # lock/web/process/browser/window
              -> agent.contracts
                  -> adapter Windows/Linux
```

Command có dạng dữ liệu rõ ràng, không phải shell string:

```python
AgentCommand(name="open_url", payload={"url": "https://example.com"})
CommandResult(command_id="...", status="success", detail="...")
```

Command allowlist ban đầu chỉ gồm action hiện có và an toàn để kiểm thử:

```text
status
open_url
block_domains
unblock_domains
start_process_guard
stop_process_guard
```

`lock_screen`/`unlock_screen` chỉ được thêm khi Agent đã có process lifecycle dài
hạn; không tạo CLI một-lệnh rồi thoát vì daemon UI/input sẽ bị dừng ngay khi process
kết thúc. Không thêm `run_shell` trong Agent; đó là rủi ro bảo mật và ngoài phạm vi.

## Việc làm ngay ngày mai

### A. Chốt command contract và application lifecycle

1. Tạo `agent/commands.py`: `AgentCommand`, `CommandResult`, enum trạng thái và
   lỗi command. Payload phải được validate theo từng command, không dùng
   `dict[str, object]` không kiểm soát ở feature.
2. Tạo `agent/application.py`: sở hữu một `AgentRuntime`, dispatcher và lifecycle
   start/shutdown. Không tạo thread/network trong module import.
3. Tạo `agent/dispatcher.py`: registry tường minh bằng mapping command-name sang
   handler; không dùng reflection hoặc execute shell.
4. Viết fake runtime/feature test cho command success, unsupported command,
   capability unavailable và feature exception.

**Xong khi:** command dispatcher có thể chạy `status` qua `AgentApplication` và
mọi test không cần desktop thật.

### B. Đưa browser và web blocker vào command handler

1. Tạo handler `open_url`; chỉ nhận URL `http://`/`https://`, gọi `open_tab` qua
   platform services đã có.
2. Tạo handler `block_domains`/`unblock_domains`; chỉ nhận path block-list được
   caller cung cấp, gọi API web blocker hiện có và trả lỗi permission rõ ràng.
3. Không đổi parser domain, marker hosts, atomic write hoặc thứ tự ưu tiên browser
   nếu không có test lỗi chứng minh cần đổi.
4. Test handler bằng fake browser/hosts adapter và temporary hosts file; test mặc
   định không ghi `/etc/hosts` hay hosts Windows.

**Xong khi:** feature được gọi bằng command data thay vì CLI logic rải rác và API
public cũ vẫn chạy.

### C. Đưa process guard vào lifecycle Agent

1. Tạo handler `start_process_guard` và `stop_process_guard` quanh `ProcessKiller`
   hiện có; một Agent chỉ có một guard đang chạy.
2. Định nghĩa rõ payload blacklist/whitelist/interval, validate process name và
   không kill process trong unit test.
3. Shutdown Agent luôn gọi `ProcessKiller.stop()` trước khi runtime đóng.
4. Test start idempotent, stop idempotent, whitelist ưu tiên và shutdown cleanup.

**Xong khi:** guard sống theo lifecycle Agent, không phụ thuộc một CLI process ngắn.

### D. Nâng `status` thành readiness report thật

1. Tách capability tĩnh khỏi readiness runtime: dependency binary, permission,
   desktop session và hosts writable phải có trạng thái riêng.
2. `status` chỉ đọc/kiểm tra an toàn; không grab input, kill process, sửa hosts,
   tạo screen overlay hoặc mở browser.
3. Output ổn định cho người và JSON-ready model cho Server tương lai; chưa cần API
   JSON/HTTP trong ngày mai.
4. Test từng readiness checker bằng dependency fake hoặc monkeypatch, không phụ
   thuộc máy dev có Xorg/Windows Administrator.

**Xong khi:** giáo viên/kỹ thuật viên biết chính xác Agent thiếu quyền hay binary
nào trước khi gửi command.

## Không làm ngày mai

- Không Server, Teacher Console, database, WebSocket, HTTP API hoặc LAN discovery.
- Không remote desktop streaming, remote input qua mạng, WebRTC hay screen relay.
- Không shell command từ xa, auto-elevation hoặc bypass quyền OS.
- Không thay classifier, input backend, screenlocker lifecycle hoặc format block
  list nếu command layer không bắt buộc phải chạm tới.

## Thứ tự sau ngày mai

1. Agent process lâu dài và local transport được kiểm thử.
2. Server tối thiểu: Agent enrollment, authentication và command relay.
3. Teacher Console tối thiểu: danh sách Agent online và gửi command allowlist.
4. Audit log/policy lớp học.
5. Screen capture theo snapshot thấp tần suất; remote desktop realtime là dự án
   sau cùng.

---

# Backlog bảo trì từ ROI audit

Chi tiết bằng chứng, phạm vi và cách kiểm chứng nằm trong
[`ROI-reports/technical-debt.md`](ROI-reports/technical-debt.md) và
[`ROI-reports/roadmap.md`](ROI-reports/roadmap.md). Không làm các mục này bằng
refactor hàng loạt.

## Đã hoàn thành

1. `screenlocker` cleanup input/overlay có lifecycle test fake, gồm lỗi UI và input
   blocker.
2. `ProcessKiller` stop/start không để daemon cũ chạy song song; health state vẫn là
   backlog riêng.
3. Web blocker dùng sidecar lock liên-process và có concurrent-worker coverage.

## P2

1. Chuẩn hóa collection/gate test, đặc biệt classifier runner phải fail khi quality
   expectation fail.
2. Tách capability tĩnh và readiness runtime trước command đặc quyền.
3. Đặt budget input/token cho classifier bằng benchmark và corpus cố định.

## P3

1. Model training deterministic, artifact manifest/hash và atomic write.
2. Bounded queue Windows input, lock state UInput Linux, và xử lý window fallback/title collision.
3. Chốt strategy dependency pin/lock và CI sau khi test gate xanh trên môi trường sạch.
