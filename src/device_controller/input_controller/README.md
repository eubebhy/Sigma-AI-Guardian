# Input Controller

File path: `src/device_controller/input_controller/README.md`

Vai tro: gui va dieu khien keyboard/mouse tren Linux hoac Windows. Input la ten
phim/nut chung, toa do hoac thoi luong; output la event dieu khien native. Package
nay cung cap resource `Input`; no khong lang nghe input hoac doc NumLock. Dung
`system_monitor.keylogger` cho hai nhu cau do.

```text
device_controller/input_controller/
├── __init__.py              # public Input resource
└── types.py                 # compatibility type

agent/platform/<os>/input_controller/
└── native sender va lifecycle cua platform
```

## Import

```python
from device_controller.input_controller import Input
```

`Input()` dung default platform services. Caller co services rieng co the truyen
`services.input_controller` vao constructor.

## Input resource

Tao mot object `Input` tu backend platform, su dung API, sau do dong resource:

```python
from device_controller.input_controller import Input

input_resource = Input()
try:
    input_resource.click()
finally:
    input_resource.close()
```

Sau `close()`, object khong con hop le va API se raise `RuntimeError`. Co the xoa
reference cua object sau khi dong. `close()` an toan khi goi lap lai.

```python
input_resource = Input(services.input_controller)
```

## Contract 15 API

Linux va Windows cung cung cap cac chu ky sau:

```python
from collections.abc import Sequence
from device_controller.input_controller.types import MouseButton

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
def close() -> None: ...
```

`click`, `mouseDown` va `mouseUp` nhan `"primary"`, `"secondary"`, `"left"`,
`"right"`, `"middle"`, `"forward"` hoac `"back"`. `keyDown`/`mouseDown` phai duoc can bang bang
`keyUp`/`mouseUp`. `write()` dung layout US/ANSI.

Toa do man hinh la so nguyen `(x, y)`: `x` tang sang phai, `y` tang xuong duoi.
`moveTo` dung toa do tuyet doi; `moveRel` dung do lech. `scroll(amount)` cuon doc,
so duong len; `sideScroll(amount)` cuon ngang, so duong sang phai.

## Backend va lifecycle

Native implementation nam trong `src/agent/platform/linux/input_controller/` va
`src/agent/platform/windows/input_controller/`, nhung chi class `Input` tai package
cha la public API. Khong co default object hoac module-level operation.

Linux can `evdev`, `python-xlib`, kernel module `uinput`, quyen ghi `/dev/uinput`,
phien X11 co `DISPLAY` va binary `xinput`. `UInputManager` giu virtual keyboard va
mouse, poll XInput2 den khi Xorg nhan dien, cache health 5 giay va tao generation
moi neu device chet. `Input.close()` dong virtual device va X11 connection da cache.
Wayland khong duoc ho tro cho API dua tren Xlib.

Windows can `pydirectinput-rgx`. Ung dung dich co dac quyen cao hon co the khong
nhan input. Mouse movement duoc thu vien noi suy thanh toa do tuyet doi de tranh
mouse acceleration.

Chay manual control shell:

```bash
./.pyvenv/bin/python tests/test_input_controller.py real control
```

Shell preload `input`, `input_help()` va tat ca method dieu khien. Goi
`input_help()` de xem huong dan API. Co the goi nhieu thao tac tren mot dong:

```python
moveTo(500, 300); click(); write("Hello"); press("enter")
```

Thoat bang `exit()`, `quit()` hoac Ctrl+D de dong `Input`. Event listener nam tai
`src/system_monitor/keylogger/`.
