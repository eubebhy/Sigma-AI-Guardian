"""Kiểm tra sender Windows chỉ bọc API pydirectinput-rgx tối thiểu."""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path
import sys
from types import ModuleType
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class _FakeDirectInput(ModuleType):
    def __init__(self) -> None:
        super().__init__("pydirectinput")
        self.calls: list[tuple[object, ...]] = []

    def press(self, keys: tuple[str, ...], **options: object) -> None:
        self.calls.append(("press", keys, options))

    def keyDown(self, key: str, **options: object) -> bool:
        self.calls.append(("keyDown", key, options))
        return True

    def keyUp(self, key: str, **options: object) -> bool:
        self.calls.append(("keyUp", key, options))
        return True

    def position(self) -> tuple[int, int]:
        self.calls.append(("position",))
        return 0, 0

    def moveTo(self, x: int, y: int, **options: object) -> None:
        self.calls.append(("moveTo", x, y, options))


class WindowWrapperTests(unittest.TestCase):
    """Wrapper không tự nội suy khi thư viện đã hỗ trợ API đó."""

    def setUp(self) -> None:
        self.fake = _FakeDirectInput()
        sys.modules["pydirectinput"] = self.fake
        sys.modules.pop("utils.input_controller.window.sendinput_kb", None)
        sys.modules.pop("utils.input_controller.window.sendinput_mouse", None)

    def tearDown(self) -> None:
        sys.modules.pop("pydirectinput", None)
        sys.modules.pop("utils.input_controller.window.sendinput_kb", None)
        sys.modules.pop("utils.input_controller.window.sendinput_mouse", None)

    def test_press_delegates_to_library(self) -> None:
        keyboard = importlib.import_module("utils.input_controller.window.sendinput_kb")

        keyboard.press(("a", "enter"))

        self.assertEqual(
            self.fake.calls,
            [("press", ("a", "enter"), {"_pause": False})],
        )

    def test_move_to_delegates_to_library(self) -> None:
        mouse = importlib.import_module("utils.input_controller.window.sendinput_mouse")

        mouse.moveTo(100, 200, duration=0.5)

        self.assertEqual(
            self.fake.calls,
            [("moveTo", 100, 200, {"duration": 0.5, "_pause": False})],
        )

    def test_root_api_uses_pyautogui_parameter_names(self) -> None:
        controller = importlib.import_module("utils.input_controller")

        self.assertEqual(
            list(inspect.signature(controller.click).parameters),
            ["x", "y", "button"],
        )
        self.assertEqual(
            list(inspect.signature(controller.moveTo).parameters),
            ["x", "y", "duration"],
        )
        self.assertEqual(
            list(inspect.signature(controller.write).parameters),
            ["message", "interval"],
        )
        self.assertFalse(hasattr(controller, "backend"))


if __name__ == "__main__":
    unittest.main()
