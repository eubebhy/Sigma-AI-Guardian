# SAG Agent Cross-Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to execute
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chuyển repository hiện có thành SAG Agent có runtime đa nền tảng rõ
ràng, giữ nguyên feature public và không thêm server hay chức năng mạng.

**Architecture:** `agent` sở hữu bootstrap, lifecycle, contracts và factory.
Adapter Linux/Windows sở hữu native command/API; feature giữ policy và gọi
contract chung. `main.py` chỉ parse CLI rồi khởi tạo Agent.

**Tech Stack:** Python 3.11+, standard library, MSS, PyWinCtl, evdev, Pyright
strict, unittest/script test hiện hữu.

## Global Constraints

- Chỉ hỗ trợ Windows 10/11 và Linux GNOME on Xorg theo README hiện tại.
- Không thêm dependency, server, network protocol, UI hay command remote mới.
- Không đổi public API đang có; dependency injection mới phải optional.
- Không reset, clean hoặc xóa các thay đổi chưa commit có trước khi làm việc.
- Module phức tạp phải có docstring tiếng Việt gồm file path, input, output và
  nguyên lý.

---

### Task 1: Khung runtime và capability

**Files:**
- Create: `src/agent/__init__.py`, `src/agent/contracts.py`,
  `src/agent/capabilities.py`, `src/agent/runtime.py`
- Create: `tests/test_agent_runtime.py`
- Modify: `src/main.py`

**Interfaces:**
- Produces: `AgentRuntime`, `PlatformServices`, `PlatformCapabilities`,
  `create_runtime(platform_name: str | None = None)`.

- [x] Viết test factory chọn Linux/Windows bằng `platform_name` giả và test CLI
  `status` không cần desktop.
- [x] Tạo contract process/browser/window/hosts nhỏ và immutable capability.
- [x] Tạo runtime chỉ chọn platform một lần, cung cấp status và shutdown.
- [x] Tạo CLI `python src/main.py status`; unsupported command trả non-zero.
- [x] Chạy `python -m unittest tests/test_agent_runtime.py` và Pyright.

### Task 2: Adapter native process và browser

**Files:**
- Create: `src/agent/platform/__init__.py`, `src/agent/platform/factory.py`
- Create: `src/agent/platform/linux/processes.py`,
  `src/agent/platform/linux/browser.py`
- Create: `src/agent/platform/windows/processes.py`,
  `src/agent/platform/windows/browser.py`
- Modify: `src/device_controler/process_killer/__init__.py`,
  `src/device_controler/browser_tab/__init__.py`
- Modify: `tests/process_killer.py`, `tests/browser_tab.py`

**Interfaces:**
- Consumes: process/browser contracts from Task 1.
- Produces: OS-neutral `list_processes`, `kill_process`, `launch_browser`.

- [x] Viết fake adapter test cho blacklist/whitelist và browser ưu tiên process
  đang chạy.
- [x] Di chuyển parser `ps`/`tasklist`, kill và Popen flags vào adapter riêng.
- [x] Inject service optional vào `ProcessKiller`; giữ `ProcessKiller()` và
  `open_tab(url)` hoạt động như cũ.
- [x] Chạy script tests không mở browser/kill process thật và Pyright.

### Task 3: Hosts và window tracking

**Files:**
- Create: `src/agent/platform/linux/hosts.py`, `src/agent/platform/windows/hosts.py`
- Create: `src/agent/platform/linux/windows.py`,
  `src/agent/platform/windows/windows.py`
- Modify: `src/device_controler/web_blocker/__init__.py`,
  `src/system_monitor/windows_tracker/__init__.py`
- Create: `tests/test_agent_platform.py`

**Interfaces:**
- Consumes: hosts/window contracts and runtime lifecycle.
- Produces: OS-resolved hosts path và normalized window API.

- [x] Test adapter selection and fake hosts/window service without system files.
- [x] Chuyển đường dẫn hosts và xdotool/PyWinCtl fallback ra adapter.
- [x] Giữ nguyên lifecycle MSS và screen locker vì chúng đã là code cross-platform.
- [x] Chạy unit tests liên quan và Pyright.

### Task 4: Hoàn thiện ranh giới, tài liệu và verification

**Files:**
- Create: `docs/architecture.md`
- Modify: `README.md`, `src/README.md`, `TODO.md`
- Test: `tests/test_agent_runtime.py`, `tests/test_agent_platform.py` và test liên quan.

**Interfaces:**
- Documents: entry point, import direction, lifecycle, capability, giới hạn OS.

- [x] Kiểm tra feature đã migration không còn gọi native OS trực tiếp.
- [x] Viết architecture doc với sơ đồ ASCII, command status, ownership và phạm vi.
- [x] Đồng bộ README chỉ với phạm vi SAG Agent; không mô tả server là đã tồn tại.
- [x] Chạy `git diff --check`, toàn bộ unittest/script test an toàn và
  `scripts/clean_pyright_check.sh src tests`.
