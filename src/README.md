# Source layout

## DESCRIPTION

`src/` chứa runtime packages của SAG. `main.py` là entry point Agent; chi tiết runtime,
contract và adapter nằm trong [architecture document](../docs/architecture.md).

## PACKAGES

| Path | Responsibility |
| --- | --- |
| `agent/` | Runtime, contracts và adapter process/browser/window/hosts Linux hoặc Windows. |
| `device_controler/` | Browser, process guard, screen, input và web blocker. |
| `system_monitor/` | Keylogger và window tracker. |
| `content_classifier/` | Rule classifier và local model classifier. |
| `utils/` | Helper không phụ thuộc feature cấp cao, gồm input blocker và key listener. |

Native platform code nằm trong `agent/platform/`, `input_controller/` và
`key_listener/` theo trách nhiệm của chúng. Feature không được import adapter
`agent.platform.linux` hoặc `agent.platform.windows` trực tiếp.

## RULES

- API public không được chặn main thread.
- Worker chạy lâu phải có owner, cleanup và test lifecycle rõ ràng.
- Module phức tạp cần module docstring nêu file path, input, output và nguyên lý.
