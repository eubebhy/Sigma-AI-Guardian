# SAG Agent roadmap

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

## Platform foundation đã hoàn thành

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
- Giữ `utils/input_blocker` là facade compatibility;
  chỉ sửa để runtime có thể dùng chúng rõ ràng hơn nếu thật sự cần.

### 3. Feature Agent

- `browser_tab`, `process_killer`, `web_blocker`, `windows_tracker` chỉ nhận
  contract/runtime chung và giữ API public cũ.
- `screen_capture` và `screenlocker` giữ nguyên lifecycle hiện có; chỉ sử dụng
  qua entry point/runtime khi feature có command Agent riêng.
- Không thêm command điều khiển mới ngoài `status`; các feature hiện hữu không
  được đổi hành vi chỉ để tái cấu trúc.

Runtime, contracts và adapter Linux/Windows đã được tách. Public API feature giữ
compatibility fallback; command dispatcher chưa tồn tại.

## Next: SAG Agent Core

Repository hiện có **platform foundation**, chưa có Agent nhận command: `main.py`
tạo `AgentRuntime`, runtime chọn `PlatformServices` Linux/Windows một lần, rồi CLI
chỉ in `status`. `AgentRuntime` không phải Server, không giao tiếp mạng và chưa sở
hữu feature chạy lâu.

```text
main.py
  -> AgentRuntime
      -> PlatformServices
          -> adapter Linux/Windows
          -> feature local
```

`PlatformServices` là túi adapter process/browser/window/hosts cho đúng OS. Các
feature mới phải nhận `runtime.services` trực tiếp. `get_default_platform_services()`
chỉ là compatibility fallback cho API cũ; xóa nó sau khi mọi feature đang dùng đã
được migration sang dependency injection.

## Phase 1: Command Core

```text
CLI hiện tại / fake transport tương lai / TCP LAN tương lai
  -> CommandRequest
  -> AgentRuntime.execute()
  -> validate action và args
  -> feature
  -> CommandResult
```

Không tạo `AgentLoop`, Poll, queue global, registry động hoặc abstraction mới chưa
cần. Transport không gọi feature trực tiếp và không tự chọn OS.

1. Thêm `CommandRequest` và `CommandResult` tối giản vào `agent.runtime`.
2. Thêm `AgentRuntime.execute(command)` với allowlist tĩnh.
3. Chỉ hỗ trợ `agent.status` trước; test action hợp lệ và action không tồn tại.
4. Thêm `classifier.rule_based` sau khi flow `status` ổn định.

**Xong khi:** CLI gọi `AgentRuntime.execute()` thay vì gọi `status()` trực tiếp; test
fake chứng minh request được validate, route và trả result mà không đụng desktop.

## Phase 2: Lifecycle feature

Feature tự quản lý worker thread; Runtime chỉ là owner của feature mà nó đã start.

```text
process_guard.start -> Runtime giữ ProcessKiller -> feature tạo worker
Agent shutdown      -> Runtime stop/close feature theo thứ tự ngược lúc start
```

1. Thêm `process_guard.start/stop` sau khi ownership và cleanup có test fake.
2. Sau đó mới thêm `keylogger.start/stop`, `screen.lock/unlock` và `LocalAI.close`.
3. Shutdown phải ngừng nhận command mới, dừng feature đang chạy và join worker có
   timeout phù hợp.
4. Hosts web block là persistent policy; không tự unblock khi Agent shutdown trừ khi
   có command policy riêng.

**Xong khi:** shutdown hợp lệ không để worker/thread của feature do Runtime sở hữu
chạy tiếp hoặc giữ input/UI state dở dang.

## Phase 3: Transport LAN

Chỉ bắt đầu sau khi Command Core và lifecycle ổn định:

```text
network packet -> CommandRequest -> AgentRuntime.execute() -> CommandResult -> packet
```

Transport chỉ encode/decode và giao tiếp mạng. Nó không biết feature, Linux/Windows
hay policy desktop. Không thêm polling hoặc persistent connection nếu chưa có yêu cầu
nghiệp vụ.

## Phase 4: Server và deployment

```text
Teacher Server <-> authenticated transport <-> Agent Core <-> Feature
```

Sau Agent Core mới quyết định TLS/authentication, systemd/OpenRC/Windows Service,
reconnect, session helper, remote input và screen streaming. Remote desktop realtime
là dự án riêng sau cùng.

## Không làm trước Phase 3

- Server, Teacher Console, database, WebSocket, HTTP API hoặc LAN discovery.
- Remote desktop streaming, remote input qua mạng, WebRTC hay screen relay.
- Shell command từ xa, auto-elevation hoặc bypass quyền OS.

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
