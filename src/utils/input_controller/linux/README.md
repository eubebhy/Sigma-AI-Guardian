# Linux input controller

Package này dùng `evdev.UInput` để tạo keyboard/mouse ảo và gửi event vào Linux.
Xorg/libinput nhận các thiết bị này rồi chuyển event tới ứng dụng đang focus.

## Cấu trúc package

```text
linux/
├── __init__.py
├── types.py
├── utils.py
├── sendinput_kb.py
├── sendinput_mouse.py
├── listener.py
└── README.md
```

### `types.py`
khai bao protocol, typealias noi bo cua package linux

### `utils.py`

Quản lý lifecycle UInput dùng chung cho keyboard/mouse:

- `create_ui()` tạo device và chờ Xorg nhận diện;
- `ui_alive()` kiểm tra fd và XInput2;
- `UInputManager` cache health trong 5 giây, đóng device chết và tạo generation
  mới để Xorg không nhầm với device cũ đang bị loại bỏ.

```text
UInputManager.get_ui()
├── cache còn hạn → trả device hiện tại
├── cache hết, device khỏe → cập nhật cache
└── device chết → close → tạo generation mới → chờ Xorg → trả device mới
```

### `sendinput_kb.py`

Khai báo capability và mapping riêng của keyboard, sau đó dùng 
`UInputManager`. Public API gồm `keyDown`, `keyUp`, `press`, `write` và helper
liệt kê phím/ký tự hỗ trợ.

### `sendinput_mouse.py`

Khai báo button/relative-axis capability và dùng một `UInputManager`. Public API
gồm click, move, scroll và position. UInput phát event; Xlib đọc vị trí cursor.

### `listener.py`

Đọc keyboard/mouse vật lý từ `/dev/input/event*`, dùng `select()` chờ event và
chuẩn hóa thành `KeyEvent` hoặc `MouseEvent`. Listener độc lập với hai sender.

### `__init__.py`

Export facade để caller import API Linux mà không cần biết hàm nằm trong file
nào.

```text
types.py → utils.py → sendinput_kb.py/sendinput_mouse.py → __init__.py → caller

physical devices → listener.py → normalized events → caller
```

## Chuẩn bị môi trường

Từ thư mục gốc dự án, tạo virtual environment và cài dependency:

```bash
python3 -m venv .pyvenv
./.pyvenv/bin/python -m pip install -r requirements.txt
./.pyvenv/bin/python -m pip install python-xlib
```

Nạp kernel module và kiểm tra `/dev/uinput`:

```bash
sudo modprobe uinput
ls -l /dev/uinput
```

Mouse position/moveTo cần chạy trong phiên X11 có `DISPLAY`:

```bash
test -n "$DISPLAY" && printf '%s\n' "$DISPLAY"
```

Chạy CLI bằng Python trong virtual environment. Nếu `sudo` không giữ biến X11,
truyền lại `DISPLAY` và `XAUTHORITY`:

```bash
sudo env DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" \
  ./.pyvenv/bin/python tests/input_controller/kb_mouse_control_cli.py \
  --move-rel 10 0 --click left
```

Logger cần quyền đọc `/dev/input/event*`:

```bash
sudo ./.pyvenv/bin/python \
  tests/input_controller/kb_mouse_event_logger.py --kb --mouse
```

## Khởi tạo virtual device trước khi gửi input

Sau khi code tạo một UInput device, Linux có thể đã tạo `/dev/input/event*`,
nhưng Xorg vẫn cần thêm một khoảng thời gian ngắn để nhìn thấy và mở device đó.
Nếu code tạo device rồi gửi event ngay, Xorg có thể chưa kịp đọc nên event đầu
tiên bị mất. Nếu process thoát ngay sau đó, device cũng bị xóa trước khi Xorg sử
dụng ổn định.

Vì vậy cần:

1. Tạo virtual keyboard/mouse trước.
2. Hỏi XInput2 cho tới khi Xorg nhìn thấy device.
3. Sau đó mới gửi event.
4. Giữ và tái sử dụng cùng device trong suốt phiên điều khiển.

`utils.py` poll XInput2 mỗi `0.067s`, tối đa `2s`. `UInputManager.get_ui()` chỉ
trả về sau khi Xorg đã nhận diện đúng device. Sau đó kết quả health được cache
5 giây để các thao tác tốc độ cao không query X11 cho mỗi event. Nếu hết thời
gian, module hủy device và báo lỗi thay vì gửi event quá sớm.

CLI `tests/input_controller/kb_mouse_control_cli.py` đang làm theo đúng thứ tự:

```text
create virtual keyboard
→ wait until Xorg sees keyboard
→ create virtual mouse
→ wait until Xorg sees mouse
→ execute actions in CLI flag order
→ exit and destroy devices
```
