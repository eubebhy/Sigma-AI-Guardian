# pyright: reportPrivateUsage=false, reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportArgumentType=false, reportAttributeAccessIssue=false
"""Unit test lifecycle đa monitor của screen locker."""

from __future__ import annotations

from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from device_controler.screen_capture import ScreenRegion
from device_controler import screenlocker


class _FakeRoot:
    def mainloop(self) -> None:
        return None

    def after(self, _: int, callback: object, *arguments: object) -> None:
        del callback, arguments

    def destroy(self) -> None:
        return None


class _FakeWindow:
    def configure(self, **options: object) -> None:
        del options

    def attributes(self, *_: object) -> None:
        return None

    def overrideredirect(self, _: bool) -> None:
        return None

    def geometry(self, _: str) -> None:
        return None


class _FakeLabel:
    def pack(self, **options: object) -> None:
        del options


class _ImmediateThread:
    def __init__(self, *, target: object, args: tuple[object, ...], **_: object) -> None:
        self._target = target
        self._args = args

    def start(self) -> None:
        assert callable(self._target)
        self._target(*self._args)

    def is_alive(self) -> bool:
        return False


class ScreenLockerTests(unittest.TestCase):
    """Screen locker phải tạo overlay cho từng monitor được cung cấp."""

    def test_run_ui_creates_one_overlay_per_monitor(self) -> None:
        first_root = _FakeRoot()
        second_root = _FakeRoot()
        regions = [
            ScreenRegion(top=0, left=0, width=1920, height=1080),
            ScreenRegion(top=0, left=1920, width=1920, height=1080),
        ]
        ready_event = threading.Event()
        failed_event = threading.Event()

        with (
            patch.object(screenlocker.tk, "Tk", return_value=first_root) as tk_root,
            patch.object(
                screenlocker.tk,
                "Toplevel",
                return_value=second_root,
            ) as top_level,
            patch.object(screenlocker, "App") as app,
            patch.object(screenlocker, "_create_lock_image", return_value=object()),
        ):
            screenlocker._run_ui(
                regions,
                ready_event,
                failed_event,
                threading.Event(),
            )

        self.assertEqual(tk_root.call_count, 1)
        self.assertEqual(top_level.call_count, 1)
        self.assertEqual(app.call_count, 2)
        self.assertTrue(ready_event.is_set())
        self.assertFalse(failed_event.is_set())

    def test_unlock_signals_ui_thread_without_calling_tkinter(self) -> None:
        stop_event = threading.Event()
        screenlocker._stop_event = stop_event

        with patch.object(screenlocker.input_blocker, "unblock") as unblock:
            screenlocker.unlock()

        self.assertTrue(stop_event.is_set())
        unblock.assert_called_once()

    def test_lock_image_uses_full_screen_brand_layout(self) -> None:
        region = ScreenRegion(top=0, left=0, width=1280, height=720)

        with patch.object(
            screenlocker.screen_capture,
            "capture",
            side_effect=AssertionError("Lock screen must not capture the desktop"),
        ):
            image = screenlocker._create_lock_image(region)

        self.assertEqual(image.size, (1280, 720))
        self.assertEqual(image.getpixel((0, 719)), (171, 1, 1))

    def test_font_size_uses_one_twenty_fifth_of_monitor_width(self) -> None:
        region = ScreenRegion(top=0, left=0, width=1920, height=1080)

        self.assertEqual(screenlocker._font_size(region), 76)

    def test_body_font_shrinks_when_text_exceeds_monitor_height(self) -> None:
        region = ScreenRegion(top=0, left=0, width=1280, height=300)

        self.assertLess(
            screenlocker._fit_body_font_size(region, header_height=50, padding=16),
            screenlocker._font_size(region),
        )

    def test_wrap_text_preserves_ascii_art_lines(self) -> None:
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        font = ImageFont.truetype(screenlocker.FONT_PATH, 16)
        art = "  title\twith tab\n /\\\n<  >\n \\_/"

        wrapped = screenlocker._wrap_text(draw, art, font, max_width=1000)

        self.assertEqual(wrapped, art)

    def test_app_keeps_photo_image_alive_on_its_label(self) -> None:
        window = _FakeWindow()
        label = _FakeLabel()
        photo = object()
        region = ScreenRegion(top=0, left=0, width=100, height=100)

        with (
            patch.object(screenlocker.ImageTk, "PhotoImage", return_value=photo),
            patch.object(screenlocker.tk, "Label", return_value=label),
        ):
            screenlocker.App(window, Image.new("RGB", (1, 1)), region)

        self.assertTrue(hasattr(label, "image"))
        self.assertIs(label.image, photo)

    def test_lock_reports_ui_startup_failure(self) -> None:
        region = ScreenRegion(top=0, left=0, width=100, height=100)
        screenlocker._thread = None

        def fail_ui(
            _: list[ScreenRegion],
            ready_event: threading.Event,
            failed_event: threading.Event,
            __: threading.Event,
        ) -> None:
            failed_event.set()
            ready_event.set()

        with (
            patch.object(screenlocker.screen_capture, "get_monitors", return_value=[region]),
            patch.object(screenlocker.threading, "Thread", _ImmediateThread),
            patch.object(screenlocker, "_run_ui", side_effect=fail_ui),
        ):
            with self.assertRaisesRegex(RuntimeError, "UI"):
                screenlocker.lock()


if __name__ == "__main__":
    unittest.main()
