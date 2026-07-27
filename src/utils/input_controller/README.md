# Input Controller

File path: `src/utils/input_controller/README.md`

Vai trò: cung cấp cùng một contract gửi và lắng nghe input cho Linux và Windows.
Input là tên phím/nút chung, tọa độ hoặc thời lượng; output là thao tác input hoặc
iterator event đã chuẩn hóa. Mỗi backend được truy cập qua facade riêng:

```text
input_controller/
├── types.py                 # kiểu dùng chung
├── linux/                   # evdev/UInput, Xlib và listener evdev
│   └── __init__.py          # facade Linux
└── window/                  # pydirectinput-rgx và pynput
    └── __init__.py          # facade Windows
```

## Import

```python
from utils.input_controller import linux
from utils.input_controller.linux import click, listen_keys

# Trên Windows, tên package theo cấu trúc hiện tại là `window`.
from utils.input_controller import window
from utils.input_controller.window import moveTo, press
```

Import facade Windows không import `pydirectinput` hoặc `pynput` ngay. Dependency
chỉ được nạp khi API sender được gọi hoặc listener bắt đầu được duyệt.

## Contract 17 API

Các chữ ký dưới đây là chữ ký thật và giống nhau giữa hai facade:

```python
from collections.abc import Iterator, Sequence
from typing import Literal

KeyEvent = tuple[str, Literal["down", "up", "hold"]]
MouseEvent = tuple[str, Literal["down", "up"]] | tuple[str, int]
MouseButton = Literal["primary", "secondary", "left", "right", "middle", "forward", "back"]

def click(
    x: int | None = None,
    y: int | None = None,
    button: MouseButton = "primary",
) -> None: ...
def get_num_lock_state() -> bool: ...
def keyDown(key: str) -> None: ...
def keyUp(key: str) -> None: ...
def listen_keys(timeout: float | None = None) -> Iterator[KeyEvent]: ...
def listen_mice(timeout: float | None = None) -> Iterator[MouseEvent]: ...
def mouseDown(button: MouseButton) -> None: ...
def mouseUp(button: MouseButton) -> None: ...
def moveRel(x: int | None, y: int | None, duration: float = 0.0) -> None: ...
def moveTo(x: int | None, y: int | None, duration: float = 0.0) -> None: ...
def position(take_new: bool = False) -> tuple[int, int]: ...
def press(keys: str | Sequence[str]) -> None: ...
def scroll(amount: int) -> None: ...
def sideScroll(amount: int) -> None: ...
def supportedKeys() -> tuple[str, ...]: ...
def supportedWriteCharacters() -> str: ...
def write(message: str, interval: float = 0.0) -> None: ...
```

`click`, `mouseDown` và `mouseUp` nhận `"left"`, `"right"`, `"middle"`,
`"forward"` hoặc `"back"`. `keyDown`/`mouseDown` phải được cân bằng bằng lời
gọi `keyUp`/`mouseUp`. `supportedKeys()` và `supportedWriteCharacters()` cho biết
input sender thực sự hỗ trợ trên backend hiện tại. `write()` dùng layout US/ANSI.

`press()` nhận một tên phím hoặc sequence tên phím. `write()` nhận text và khoảng
`interval` giữa các ký tự; đặt `interval=0` để không chờ.

`get_num_lock_state()` là API thứ 17 chung giữa hai facade; nó trả trạng thái NumLock
hiện tại khi backend có thể đọc được trạng thái này.

## Tọa độ và cuộn

Tọa độ màn hình là số nguyên `(x, y)`: `x` tăng sang phải, `y` tăng xuống dưới.
`moveTo` dùng tọa độ tuyệt đối; `moveRel` dùng độ lệch từ vị trí hiện tại.
`duration` là tổng thời gian tính bằng giây. `position(take_new=False)` giữ cùng chữ
ký trên hai backend; Windows bỏ qua `take_new`.

`scroll(amount)` cuộn dọc, số dương lên và số âm xuống. `sideScroll(amount)`
cuộn ngang, số dương sang phải và số âm sang trái. Giá trị `0` không tạo độ dịch.

## Event và listener

Các kiểu trong `utils.input_controller.types` được dùng chung:

```python
KeyEvent = tuple[str, Literal["down", "up", "hold"]]
MouseEvent = (
    tuple[str, Literal["down", "up"]]
    | tuple[str, int]
)
```

Keyboard trả tên `KEY_*`, ví dụ `("KEY_A", "down")`. Mouse trả nút `BTN_*`,
chuyển động `REL_X`/`REL_Y` và cuộn `REL_WHEEL`/`REL_HWHEEL`.

`timeout` là thời gian tối đa của mỗi lần chờ nội bộ, không phải thời hạn sống
của iterator và không làm iterator tự kết thúc khi chưa có event. Listener tiếp
tục chờ cho tới khi caller đóng generator hoặc backend lỗi. Trên Windows, đóng
generator luôn gọi `stop()` rồi `join()` hook nền; hook chết ngoài ý muốn gây
`RuntimeError`. Trên Linux, generator đọc các device vật lý trong vòng lặp
`select()` và kết thúc khi caller đóng generator.

## Điều kiện và giới hạn backend

Linux cần `evdev`, `python-xlib`, kernel module `uinput`, quyền ghi
`/dev/uinput`, quyền đọc `/dev/input/event*`, và phiên X11 có `DISPLAY` để đọc
hoặc di chuyển con trỏ. Backend hiện không hỗ trợ Wayland cho API dựa trên Xlib.

Windows cần `pydirectinput-rgx` để gửi input và `pynput` để hook listener.
Keyboard sender chỉ gõ các ký tự US/ANSI do helper công bố và chỉ ánh xạ các tên
phím Windows hỗ trợ; text đầu ra còn phụ thuộc keyboard layout đang active.
Ứng dụng đích có đặc quyền cao hơn có thể không nhận input. Mouse movement được
nội suy thành tọa độ tuyệt đối để tránh mouse acceleration. Listener phụ thuộc
khả năng cài global hook của phiên desktop hiện tại; `pynput` không thể phân biệt
hoàn hảo một số phím keypad và navigation có cùng biểu diễn trên Windows.
