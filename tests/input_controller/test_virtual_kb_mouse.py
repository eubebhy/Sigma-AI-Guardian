# pyright: reportPrivateUsage=false
"""Unit test virtual keyboard, virtual mouse và input listener Linux.

File path: `tests/input_controller/test_virtual_kb_mouse.py`
Input: module `sendinput_kb` và `sendinput_mouse` với một `UInput` giả để ghi
lại capability/event; listener dùng fake input device và fake `select`.
Output: xác nhận virtual device được tạo đúng và listener chuẩn hóa event đúng.
Nguyên lý test: thay `evdev.UInput` thật bằng object giả, xác nhận import chưa tạo
device, rồi gọi `_get_ui()` để bắt capability và event.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from importlib import util
from pathlib import Path
from types import ModuleType
from typing import Callable, ClassVar, cast
from unittest.mock import patch

import evdev
from evdev import ecodes

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from utils.input_controller import linux as linux_api
from utils.input_controller.linux import listener


class _FakeUInput:
    last_instance: ClassVar[_FakeUInput | None] = None

    def __init__(self, capabilities: dict[int, list[int]], name: str = "") -> None:
        # Giả lập UInput để bắt lại capability lúc module được import.
        type(self).last_instance = self
        self.capabilities = capabilities
        self.name = name
        self.writes: list[tuple[int, int, int]] = []
        self.synced = 0

    def write(self, event_type: int, code: int, value: int) -> None:
        self.writes.append((event_type, code, value))

    def syn(self) -> None:
        self.synced += 1


class _FakePointer:
    root_x = 10
    root_y = 20


class _FakeRoot:
    def query_pointer(self) -> _FakePointer:
        return _FakePointer()


class _FakeEvent:
    def __init__(self, event_type: int, code: int, value: int) -> None:
        self.type = event_type
        self.code = code
        self.value = value


class _FakeInputDevice:
    def __init__(
        self,
        events: list[_FakeEvent],
        capabilities: dict[int, list[int]] | None = None,
    ) -> None:
        self._events = events
        self._capabilities = capabilities or {}

    def fileno(self) -> int:
        return 0

    def capabilities(self, verbose: bool = False, absinfo: bool = True) -> object:
        return self._capabilities

    def read(self) -> Iterator[_FakeEvent]:
        return iter(self._events)


def _load_module(module_name: str) -> tuple[ModuleType, _FakeUInput]:
    # Import không được mở `/dev/uinput`; device chỉ tạo khi `_get_ui()` được gọi.
    sys.modules.pop(module_name, None)
    _FakeUInput.last_instance = None
    with patch.object(evdev, "UInput", _FakeUInput):
        module = importlib.import_module(module_name)
        assert _FakeUInput.last_instance is None
        get_ui = cast(Callable[[], object], getattr(module, "_get_ui"))
        get_ui()

    fake = _FakeUInput.last_instance
    assert fake is not None
    return module, fake


def _load_control_cli() -> ModuleType:
    path = Path(__file__).with_name("kb_mouse_control_cli.py")
    spec = util.spec_from_file_location("kb_mouse_control_cli", path)
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_keyboard_supports_basic_keys_and_helpers() -> None:
    """Virtual keyboard khai báo đủ phím basic và gửi đúng chuỗi event."""

    module, fake = _load_module("utils.input_controller.linux.sendinput_kb")
    expected_keys = [
        ecodes.KEY_A,
        ecodes.KEY_Z,
        ecodes.KEY_0,
        ecodes.KEY_F1,
        ecodes.KEY_F12,
        ecodes.KEY_LEFTCTRL,
        ecodes.KEY_RIGHTCTRL,
        ecodes.KEY_SPACE,
        ecodes.KEY_ENTER,
        ecodes.KEY_UP,
        ecodes.KEY_DOWN,
        ecodes.KEY_LEFT,
        ecodes.KEY_RIGHT,
        ecodes.KEY_KP0,
        ecodes.KEY_KPENTER,
    ]

    # Bàn phím ảo phải khai báo các phím phổ biến để app khác nhận đúng.
    assert fake.name == "Sigma Virtual Keyboard"
    assert fake.capabilities[ecodes.EV_REP] == []
    for code in expected_keys:
        assert code in fake.capabilities[ecodes.EV_KEY]
    assert ecodes.KEY_ZENKAKUHANKAKU not in fake.capabilities[ecodes.EV_KEY]
    assert len(fake.capabilities[ecodes.EV_KEY]) == len(
        set(fake.capabilities[ecodes.EV_KEY])
    )

    # Chạy qua toàn bộ phím basic để bắt đúng mapping KEY_* -> evdev code.
    supported_key_names: list[tuple[str, int]] = []
    for code in module._KEY_CODES:
        for name, mapped_code in ecodes.ecodes.items():
            if mapped_code == code and name.startswith("KEY_"):
                supported_key_names.append((name.removeprefix("KEY_").lower(), code))
                break

    expected_writes: list[tuple[int, int, int]] = []
    for key_name, code in supported_key_names:
        module.keyDown(key_name)
        module.keyUp(key_name)
        expected_writes.extend(
            [
                (ecodes.EV_KEY, code, 1),
                (ecodes.EV_KEY, code, 2),
                (ecodes.EV_KEY, code, 0),
            ],
        )

    assert fake.writes == expected_writes
    assert fake.synced == len(supported_key_names) * 2

    synced_before_press = fake.synced
    fake.writes.clear()
    module.press("a", delay=0)
    assert fake.writes == [
        (ecodes.EV_KEY, ecodes.KEY_A, 1),
        (ecodes.EV_KEY, ecodes.KEY_A, 2),
        (ecodes.EV_KEY, ecodes.KEY_A, 0),
    ]
    assert fake.synced == synced_before_press + 2


def test_linux_package_exports_public_api() -> None:
    """Package Linux phải export các thao tác keyboard, mouse và listener."""

    for name in (
        "keyDown",
        "keyUp",
        "press",
        "write",
        "click",
        "mouseDown",
        "mouseUp",
        "moveTo",
        "moveRel",
        "scroll",
        "sideScroll",
        "position",
        "listen_keys",
        "listen_mice",
    ):
        assert callable(getattr(linux_api, name))


def test_control_cli_prepares_devices_before_actions() -> None:
    """Control CLI phải tạo kb/mouse và chờ trước khi gửi action đầu tiên."""

    module = _load_control_cli()
    prepare = getattr(module, "_prepare_devices", None)
    assert callable(prepare)
    calls: list[object] = []
    with (
        patch.object(
            getattr(module, "sendinput_kb"),
            "_get_ui",
            side_effect=lambda: calls.append("kb"),
        ),
        patch.object(
            getattr(module, "sendinput_mouse"),
            "_get_ui",
            side_effect=lambda: calls.append("mouse"),
        ),
        patch.object(
            getattr(module, "time"),
            "sleep",
            side_effect=calls.append,
        ),
    ):
        prepare()

    assert calls == ["kb", "mouse", 0.67]


def test_mouse_supports_click_buttons() -> None:
    """Mouse virtual device phải khai báo đủ nút cho click."""

    _, fake = _load_module("utils.input_controller.linux.sendinput_mouse")
    assert fake.capabilities[ecodes.EV_KEY] == [
        ecodes.BTN_LEFT,
        ecodes.BTN_RIGHT,
        ecodes.BTN_MIDDLE,
        ecodes.BTN_FORWARD,
        ecodes.BTN_BACK,
    ]


def test_mouse_move_rel_writes_relative_events() -> None:
    """`moveRel()` phải phát REL_X/REL_Y theo từng bước."""

    module, fake = _load_module("utils.input_controller.linux.sendinput_mouse")
    module.moveRel(10, -5, steps=2)

    assert fake.writes == [
        (ecodes.EV_REL, ecodes.REL_X, 5),
        (ecodes.EV_REL, ecodes.REL_Y, -2),
        (ecodes.EV_REL, ecodes.REL_X, 5),
        (ecodes.EV_REL, ecodes.REL_Y, -3),
    ]
    assert fake.synced == 2


def test_mouse_move_to_uses_current_position() -> None:
    """`moveTo()` phải đổi tọa độ tuyệt đối thành move tương đối."""

    module, fake = _load_module("utils.input_controller.linux.sendinput_mouse")
    setattr(module, "_root", _FakeRoot())
    move_to = cast(Callable[[int, int], None], getattr(module, "moveTo"))
    move_to(15, 17)

    assert fake.writes == [
        (ecodes.EV_REL, ecodes.REL_X, 5),
        (ecodes.EV_REL, ecodes.REL_Y, -3),
    ]
    assert fake.synced == 1


def test_mouse_scroll_writes_vertical_and_horizontal_events() -> None:
    """Scroll dọc/ngang phải dùng đúng relative axis."""

    module, fake = _load_module("utils.input_controller.linux.sendinput_mouse")
    module.scroll(-2)
    module.sideScroll(3)

    assert ecodes.REL_HWHEEL in fake.capabilities[ecodes.EV_REL]
    assert fake.writes == [
        (ecodes.EV_REL, ecodes.REL_WHEEL, -2),
        (ecodes.EV_REL, ecodes.REL_HWHEEL, 3),
    ]
    assert fake.synced == 2


def test_listener_normalizes_kb_and_mouse_events() -> None:
    """Listener phải chuẩn hóa keyboard, button và relative motion event."""

    keyboard = _FakeInputDevice([_FakeEvent(ecodes.EV_KEY, ecodes.KEY_A, 1)])
    listener._keyboards = [keyboard]
    with patch.object(listener.select, "select", return_value=([keyboard], [], [])):
        assert next(listener.listen_keys()) == ("KEY_A", "down")

    mouse = _FakeInputDevice(
        [
            _FakeEvent(ecodes.EV_KEY, ecodes.BTN_LEFT, 0),
            _FakeEvent(ecodes.EV_REL, ecodes.REL_X, 12),
        ]
    )
    listener._mice = [mouse]
    with patch.object(listener.select, "select", return_value=([mouse], [], [])):
        events = listener.listen_mice()
        assert next(events) == ("BTN_LEFT", "up")
        assert next(events) == ("REL_X", 12)


def test_listener_detects_devices_and_reports_missing_devices() -> None:
    """Listener phải nhận diện keycode thật và báo khi thiếu device."""

    keyboard = _FakeInputDevice(
        [],
        {ecodes.EV_KEY: list(listener._LETTER_CODES)},
    )
    assert listener._is_keyboard(keyboard)

    with patch.object(listener, "_get_keyboards", return_value=[]):
        try:
            next(listener.listen_keys())
        except RuntimeError as error:
            assert str(error) == "No Linux keyboard input device found"
        else:
            raise AssertionError("listen_keys() did not report missing device")

    with patch.object(listener, "_get_mice", return_value=[]):
        try:
            next(listener.listen_mice())
        except RuntimeError as error:
            assert str(error) == "No Linux mouse input device found"
        else:
            raise AssertionError("listen_mice() did not report missing device")


def main() -> None:
    test_keyboard_supports_basic_keys_and_helpers()
    test_linux_package_exports_public_api()
    test_control_cli_prepares_devices_before_actions()
    test_mouse_supports_click_buttons()
    test_mouse_move_rel_writes_relative_events()
    test_mouse_move_to_uses_current_position()
    test_mouse_scroll_writes_vertical_and_horizontal_events()
    test_listener_normalizes_kb_and_mouse_events()
    test_listener_detects_devices_and_reports_missing_devices()


if __name__ == "__main__":
    main()
    print("PASS: virtual kb and mouse")
