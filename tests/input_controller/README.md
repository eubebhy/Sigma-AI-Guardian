# Input controller Linux

| File | Mục đích | Cách chạy |
| --- | --- | --- |
| `test_virtual_kb_mouse.py` | Unit test virtual kb/mouse và listener bằng fake device. | `python3 tests/input_controller/test_virtual_kb_mouse.py` |
| `kb_mouse_event_logger.py` | Ghi event thật, chọn `--kb`, `--mouse` hoặc cả hai. | `sudo python3 tests/input_controller/kb_mouse_event_logger.py --kb` |
| `kb_mouse_control_cli.py` | Gọi tuần tự API kb/mouse thật theo thứ tự flag. | `sudo python3 tests/input_controller/kb_mouse_control_cli.py --help` |

Unit test không cần quyền thiết bị. Logger cần quyền đọc `/dev/input/event*`;
control CLI cần quyền ghi `/dev/uinput` và kết nối X11 cho position/moveTo.

