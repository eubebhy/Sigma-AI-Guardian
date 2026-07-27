# Input Controller

File path: `src/device_controler/input_controller/README.md`

Vai tro: gui va dieu khien keyboard/mouse tren Linux hoac Windows. Input la ten
phim/nut chung, toa do hoac thoi luong; output la event dieu khien native. Package
nay khong lang nghe input hoac doc NumLock; dung `utils.key_listener` cho hai nhu
cau do.

```text
input_controller/
├── types.py                 # Key, MouseButton va InputBackend
├── linux/                   # evdev/UInput, Xlib va lifecycle virtual device
│   └── __init__.py          # facade sender Linux
└── window/                  # pydirectinput-rgx / WinAPI SendInput
    └── __init__.py          # facade sender Windows
```

## Import

```python
from device_controler import input_controller
from device_controler.input_controller import linux
from device_controler.input_controller.linux import click, moveTo

# Package backend Windows giu ten `window`.
from device_controler.input_controller import window
from device_controler.input_controller.window import press, write
```

Import facade Windows khong import `pydirectinput` ngay. Dependency chi duoc nap
khi API sender duoc goi.

## Contract 14 API

Linux va Windows cung cung cap cac chu ky sau:

```python
from collections.abc import Sequence
from device_controler.input_controller.types import MouseButton

def click(
    x: int | None = None,
    y: int | None = None,
    button: MouseButton = "primary",
) -> None: ...
def keyDown(key: str) -> None: ...
def keyUp(key: str) -> None: ...
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

`click`, `mouseDown` va `mouseUp` nhan `"left"`, `"right"`, `"middle"`,
`"forward"` hoac `"back"`. `keyDown`/`mouseDown` phai duoc can bang bang
`keyUp`/`mouseUp`. `write()` dung layout US/ANSI.

Toa do man hinh la so nguyen `(x, y)`: `x` tang sang phai, `y` tang xuong duoi.
`moveTo` dung toa do tuyet doi; `moveRel` dung do lech. `scroll(amount)` cuon doc,
so duong len; `sideScroll(amount)` cuon ngang, so duong sang phai.

## Backend va lifecycle

Linux can `evdev`, `python-xlib`, kernel module `uinput`, quyen ghi `/dev/uinput`,
phien X11 co `DISPLAY` va binary `xinput`. `UInputManager` giu virtual keyboard va
mouse, poll XInput2 den khi Xorg nhan dien, cache health 5 giay va tao generation
moi neu device chet. Wayland khong duoc ho tro cho API dua tren Xlib.

Windows can `pydirectinput-rgx`. Ung dung dich co dac quyen cao hon co the khong
nhan input. Mouse movement duoc thu vien noi suy thanh toa do tuyet doi de tranh
mouse acceleration.

Xem kiem thu manual control tai `tests/test_input_controller.py` va event listener
tai [`src/utils/key_listener/README.md`](../../utils/key_listener/README.md).
