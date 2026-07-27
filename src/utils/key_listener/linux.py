"""Lắng nghe input và đọc NumLock trên Linux qua evdev/X11.

File path: `src/utils/key_listener/linux.py`
Input: các device `/dev/input/event*` có capability phím A-Z.
Output: generator event chuẩn hóa và trạng thái NumLock hiện tại.
Nguyên lý: quét danh sách device một lần rồi cache lại để tránh IO lặp; vòng lặp
chính dùng `select` để chỉ đọc device khi kernel báo có event sẵn. NumLock dùng
kết nối X11 ngắn hạn để không chia sẻ lifecycle với input injection.
"""

from collections.abc import Callable, Iterator, Sequence
import select
from typing import Final, Protocol, cast

import evdev
from evdev import InputDevice, ecodes
from Xlib.display import Display

from utils.key_listener.types import KeyEvent, KeyState, MouseEvent, MouseState

# InputDevice truyen path vao duoi dang str thay vi Pat
# It nhat quyet dinh tren chi la tam thoi


class _InputEvent(Protocol):
    type: int
    code: int
    value: int


class _InputDevice(Protocol):
    """Phần tối thiểu của `evdev.InputDevice` mà listener cần.

    Dùng Protocol thay vì `InputDevice[str]` vì stub evdev giữa các môi trường có
    nơi xem `InputDevice` là generic, có nơi không. Protocol chỉ kiểm tra object
    có đủ hàm cần dùng, nên vẫn type-check được mà runtime không đổi.
    """

    def fileno(self) -> int:
        """Cho phép truyền device vào `select.select()`."""
        ...

    def capabilities(self, verbose: bool = False, absinfo: bool = True) -> object:
        """Trả capability để phân biệt keyboard và mouse."""
        ...

    def read(self) -> Iterator[_InputEvent]:
        """Đọc các event đang chờ từ device."""
        ...


_keyboards: list[_InputDevice] = []
_mice: list[_InputDevice] = []
_LETTER_CODES: Final[tuple[int, ...]] = (
    ecodes.KEY_A,
    ecodes.KEY_B,
    ecodes.KEY_C,
    ecodes.KEY_D,
    ecodes.KEY_E,
    ecodes.KEY_F,
    ecodes.KEY_G,
    ecodes.KEY_H,
    ecodes.KEY_I,
    ecodes.KEY_J,
    ecodes.KEY_K,
    ecodes.KEY_L,
    ecodes.KEY_M,
    ecodes.KEY_N,
    ecodes.KEY_O,
    ecodes.KEY_P,
    ecodes.KEY_Q,
    ecodes.KEY_R,
    ecodes.KEY_S,
    ecodes.KEY_T,
    ecodes.KEY_U,
    ecodes.KEY_V,
    ecodes.KEY_W,
    ecodes.KEY_X,
    ecodes.KEY_Y,
    ecodes.KEY_Z,
)


def _is_keyboard(device: _InputDevice) -> bool:
    """Trả về `True` nếu device có đủ nhóm phím chữ cái A-Z."""

    # Doc: https://python-evdev.readthedocs.io/en/latest/tutorial.html#listing-device-capabilities
    capabilities = cast(dict[int, Sequence[int]], device.capabilities(absinfo=False))
    keys = capabilities.get(ecodes.EV_KEY, [])

    return all(code in keys for code in _LETTER_CODES)


def _get_keyboards() -> list[_InputDevice]:
    """Trả về danh sách keyboard đã cache để không quét `/dev/input` nhiều lần."""

    global _keyboards

    if _keyboards:
        return _keyboards

    keyboards: list[_InputDevice] = []

    # Stub evdev khai báo `list_devices` chưa đủ rõ, nên cast để Pyright biết
    # hàm này nhận thư mục input và trả về danh sách path dạng chuỗi.
    list_devices = cast(
        Callable[[str], list[str]],
        getattr(cast(object, evdev), "list_devices"),
    )

    for path in list_devices("/dev/input"):
        device = InputDevice(path)

        if _is_keyboard(device):
            keyboards.append(device)

    _keyboards = keyboards

    return keyboards


def get_num_lock_state() -> bool:
    """Trả trạng thái NumLock hiện tại từ X11 keyboard control."""

    display = Display()
    try:
        return bool(display.get_keyboard_control().led_mask & 2)
    finally:
        display.close()


def listen_keys(timeout: float | None = None) -> Iterator[KeyEvent]:
    """Sinh keyboard event đã chuẩn hóa từ device evdev.

    `timeout=None` chờ vô hạn trong `select`; số giây cụ thể giúp caller tự
    thoát vòng lặp định kỳ mà không phải polling liên tục.
    """

    keyboards: list[_InputDevice] = _get_keyboards()
    if not keyboards:
        raise RuntimeError("No Linux keyboard input device found")

    while True:
        readable, _, _ = select.select(keyboards, [], [], timeout)

        for device in readable:
            read_events = cast(
                Callable[[], Iterator[_InputEvent]], getattr(device, "read")
            )

            for event in read_events():
                if event.type == ecodes.EV_KEY:
                    code = cast(str, ecodes.KEY[event.code])

                    if event.value == 0:
                        value: KeyState = "up"
                    elif event.value == 1:
                        value = "down"
                    elif event.value == 2:
                        value = "hold"
                    else:
                        raise RuntimeError(f"Unknown value for keyboard: {event.value}")

                    yield code, value


def _is_mouse(device: _InputDevice) -> bool:
    """Trả về `True` nếu device có may phim left, middle, right"""

    # Chi nen dinh nghia chuot co left
    # Viet them qua nhieu dieu kien de bo lo thiet bi nhu touchpad
    capabilities = cast(dict[int, Sequence[int]], device.capabilities(absinfo=False))
    keys = capabilities.get(ecodes.EV_KEY, [])

    return all(code in keys for code in [ecodes.BTN_LEFT])


def _get_mice() -> list[_InputDevice]:
    global _mice

    if _mice:
        return _mice

    mice: list[_InputDevice] = []

    # Giống `_get_keyboards()`: giữ runtime evdev gốc, chỉ làm rõ type cho checker.
    list_devices = cast(
        Callable[[str], list[str]],
        getattr(cast(object, evdev), "list_devices"),
    )

    for path in list_devices("/dev/input"):
        device = InputDevice(path)

        if _is_mouse(device):
            mice.append(device)

    _mice = mice

    return mice


def listen_mice(timeout: float | None = None) -> Iterator[MouseEvent]:
    """Sinh mouse event gồm nút chuột, di chuyển tương đối và cuộn."""

    mice: list[_InputDevice] = _get_mice()
    if not mice:
        raise RuntimeError("No Linux mouse input device found")

    while True:
        readable, _, _ = select.select(
            mice, [], [], timeout
        )  # Hoc theo docs tren evdev, toi chua thuc su hieu doan nay lam

        for device in readable:
            read_events = cast(
                Callable[[], Iterator[_InputEvent]], getattr(device, "read")
            )

            for event in read_events():
                if event.type == ecodes.EV_KEY:
                    # Một vài device chuột/touchpad cũng phát KEY_* phụ; listener
                    # chuột chỉ trả nút BTN_* để không lẫn phím bàn phím.
                    if event.code < ecodes.BTN_MOUSE:
                        continue

                    code_name = ecodes.keys[event.code]
                    code = code_name[0] if isinstance(code_name, tuple) else code_name

                    if event.value == 0:
                        value: MouseState = "up"
                    elif event.value == 1:
                        value = "down"
                    elif event.value == 2:
                        continue
                    else:
                        raise RuntimeError(f"Unknown value for mouse: {event.value}")

                    yield code, value

                elif event.type == ecodes.EV_REL:
                    code = cast(str, ecodes.REL[event.code])
                    yield code, event.value


__all__ = ["get_num_lock_state", "listen_keys", "listen_mice"]
