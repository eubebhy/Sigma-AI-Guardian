# Key Listener

File path: `src/utils/key_listener/README.md`

Vai tro: compatibility facade lang nghe keyboard/mouse va doc NumLock theo Linux
hoac Windows qua `PlatformServices.key_listener`. Input la
`timeout`, `stop_event` tuy chon cho moi lan cho event hoac loi goi doc NumLock;
output la generator event da chuan hoa va `bool`. Module khong gui input; dung
`device_controller.input_controller` cho control.

```text
utils/key_listener/
├── types.py                 # compatibility event type
├── linux.py                 # compatibility API Linux
├── windows.py               # compatibility API Windows
└── __init__.py              # public facade qua Agent platform service

agent/platform/<os>/key_listener_backend.py
└── native evdev/X11 hoac pynput/Win32
```

## Import va contract

```python
from utils.key_listener import (
    KeyEvent,
    get_num_lock_state,
    listen_keys,
    listen_mice,
)

for event in listen_keys(timeout=0.1):
    print(event)
```

`KeyEvent` la `tuple[str, Literal["down", "up", "hold"]]`. `MouseEvent` la
button event `tuple[str, Literal["down", "up"]]` hoac relative motion/scroll
event `tuple[str, int]`. Keyboard tra ten `KEY_*`; mouse tra `BTN_*`, `REL_X`,
`REL_Y`, `REL_WHEEL` hoac `REL_HWHEEL`.

`timeout` chi gioi han mot lan cho noi bo, khong tu dong ket thuc iterator.
`stop_event` ket thuc iterator o lan cho ke tiep; khi co stop event va timeout mac
dinh, Linux kiem tra stop toi da sau 0.1 giay. Windows dong generator se `stop()` va
`join()` hook; Linux doc device vat ly trong vong lap `select()`.
`get_num_lock_state()` doc X11 tren Linux va Win32 `user32` tren Windows.

Linux can quyen doc `/dev/input/event*`; Windows can `pynput` va kha nang cai global
hook trong desktop session. Chay logger manual co chu dich:

```bash
sudo ./.pyvenv/bin/python tests/test_key_listener.py real logger --kb --mouse
```
