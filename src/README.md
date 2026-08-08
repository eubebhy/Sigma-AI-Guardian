# Source layout

## DESCRIPTION

`src/` chứa runtime packages của SAG. `main.py` là entry point Agent; chi tiết runtime,
protocol và adapter nằm trong [architecture document](../docs/architecture.md).

## PACKAGES

| Path | Responsibility |
| --- | --- |
| `agent/` | Runtime, lifecycle protocols, platform protocols và adapter process/browser/window/hosts/input Linux hoặc Windows. |
| `device_controller/` | Browser, process guard, screen, input và web blocker. |
| `system_monitor/` | Keylogger và window tracker. |
| `content_classifier/` | Rule classifier và local model classifier. |
| `utils/` | Compatibility facade cho input blocker/key listener và helper dùng chung. |

Native platform code nằm trong `agent/platform/`. Compatibility facade không được
chứa OS selection hoặc native implementation. Feature không được import adapter
`agent.platform.linux` hoặc `agent.platform.windows` trực tiếp.

## RULES

- API public không được chặn main thread.
- Worker chạy lâu phải có owner, cleanup và test lifecycle rõ ràng.
- Module phức tạp cần module docstring nêu file path, input, output và nguyên lý.

## DOCUMENTATION STATUS

File này mô tả layout hiện tại. Các tài liệu kiến trúc và guide có thể lỗi thời khi
đổi `AgentRuntime`, protocol, adapter hoặc compatibility facade; thay đổi boundary
phải cập nhật tài liệu cùng commit.
