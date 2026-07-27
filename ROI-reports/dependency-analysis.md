# Phân tích dependency và tái lập môi trường

## TL;DR

`requirements.txt` có 14 dependency runtime chưa pin/hash; không có lockfile hay
dev-tool dependency. Venv audit có `pip check` sạch, nhưng Pyright lấy từ global PATH
và không resolve `pyperclip` trong `scripts/record_clip_board.py`.

## Mapping trực tiếp

| Dependency | Consumer đã xác nhận | Ghi chú |
| --- | --- | --- |
| `pyperclip` | `scripts/record_clip_board.py` | Pyright hiện báo unresolved trong script. |
| `scikit-learn`, `joblib` | local classifier, trainer | `joblib` artifact là trust boundary. |
| `Pillow` | screen locker | Tk/Pillow rendering desktop. |
| `PyWinCtl` | Windows/Linux window adapters | Optional behavior phụ thuộc desktop. |
| `numpy`, `mss` | screen capture | Capture không được automated test với desktop thật. |
| `evdev`, `python-xlib` | Linux input | Có platform marker Linux. |
| `pydirectinput-rgx`, `pynput` | Windows input | Có platform marker Windows. |
| `rapidfuzz` | Không thấy import Python tracked | Giữ nguyên tới khi maintainer xác nhận intent. |

## Rủi ro bảo trì

- Không pin version/hash: không tái lập hoàn toàn build/test; dependency transitive có
  thể đổi hành vi.
- Không có `pyproject.toml`, lockfile hoặc dev requirements: setup tooling dựa PATH
  máy developer.
- `clean_pyright_check.sh` phụ thuộc global `pyright` và `jq`; stderr bị ẩn và warning
  hiện không fail command.
- Linux virtual mouse gọi `xinput`, nhưng hướng dẫn hệ thống phải liệt kê binary này.

## Lộ trình tối thiểu

1. Xác nhận Python/OS support matrix và giữ runtime/dev dependency tách rõ.
2. Tạo môi trường sạch trên Linux/Windows, resolve version đã chọn và ghi chiến lược
   pin/lock có owner. Không pin mù theo venv hiện tại.
3. Chạy smoke import theo platform marker và `pip check` trong CI.
4. Chỉ loại `rapidfuzz` khi history/maintainer xác nhận không phải API/dự định gần.

## Verification đề xuất

Fresh venv phải cài, chạy `src/main.py status`, unit tests an toàn và type check.
Windows/Linux native feature vẫn cần manual matrix, không được giả vờ coverage bằng
CI Linux-only.
