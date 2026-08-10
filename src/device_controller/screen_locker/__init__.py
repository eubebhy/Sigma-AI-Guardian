# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportAttributeAccessIssue=false
"""Khóa màn hình đa monitor trên Windows và Linux.

File path: `src/device_controller/screen_locker/__init__.py`.
Input: `lock()` và `unlock()` không nhận tham số.
Output: `lock()` phủ mọi monitor bằng thông báo khóa rồi chặn input; nó raise lỗi nếu
UI không duy trì trạng thái sẵn sàng. `unlock()` trả `True` khi input và UI cleanup
thành công, hoặc raise lỗi cleanup.
Nguyên lý: Pillow dựng một ảnh khóa theo đúng độ phân giải từng monitor; Tkinter
hiển thị ảnh toàn màn hình. UI thread block input sau khi tạo overlay và tự unblock
khi đóng; `unlock()` signal rồi chờ UI cleanup. Lock/unlock được serialize để không
một `unlock()` thành
công trước khi một `lock()` đang khởi tạo hoàn tất. Lỗi UI được lưu bằng event để
`unlock()` báo cho caller.
"""

import threading
import tkinter as tk
from pathlib import Path
from typing import NoReturn, cast

from PIL import Image, ImageDraw, ImageFont, ImageTk

from agent.platform_protocols import CursorOperations, InputBlockingOperations
from agent.platform import get_default_platform_services
from device_controller import screen_capture
from utils import input_blocker


FONT_PATH = Path(__file__).with_name("unscii-8.ttf")
BACKGROUND_COLOR = "#ab0101"
TEXT_COLOR = "#FFFFFF"
DEFAULT_LOCK_HEADER = "Oops, system is locked by SIGMA AI GUARDIAN"
DEFAULT_LOCK_MESSAGE = """
Your workstation has been restricted for one of the following reasons:

The administrator has manually locked your machine.
The system automatically locked it after detecting prohibited or unauthorized 
activity.

Contact your administrator immediately.
While waiting for unlock, you are strictly required to follow these rules:

    1. Do not turn off the computer. Keep the power supply stable at all times.
    
    2. Do not attempt to bypass, force-close, restart, or interfere with the
       locking system in any way.

    3. Remain at the computer and wait for the administrator to unlock it. 

Improper shutdown or unauthorized interference with the system may result in 
UNINTENDED CONSEQUENCES.
"""
_lock = threading.RLock()
_thread: threading.Thread | None = None
_stop_event: threading.Event | None = None
_ui_exited_event: threading.Event | None = None
_ui_failed_event: threading.Event | None = None
_ui_error: Exception | None = None
_input_operations: InputBlockingOperations | None = None
_UI_EXIT_TIMEOUT_SECONDS = 5.0


class ScreenLockOverlay:
    """Tạo một overlay topmost cho một monitor."""

    def __init__(
        self,
        root: tk.Tk | tk.Toplevel,
        image: Image.Image,
        region: screen_capture.ScreenRegion,
    ) -> None:
        photo = ImageTk.PhotoImage(image)
        root.configure(bg="black")
        root.attributes("-topmost", True)
        root.overrideredirect(True)
        root.geometry(f"{region.width}x{region.height}{region.left:+d}{region.top:+d}")
        label = tk.Label(root, bg="black", image=photo)
        label.image = photo
        label.pack(expand=True, fill="both")


def _font_size(region: screen_capture.ScreenRegion) -> int:
    """Đặt glyph vuông bằng một phần hai mươi lăm chiều rộng monitor."""

    return max(8, min(region.width // 25, region.height // 12))


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> str:
    """Trả body nguyên văn để giữ mọi khoảng trắng, tab và ASCII art."""

    del draw, font, max_width
    return text


def _fit_body_font_size(
    region: screen_capture.ScreenRegion,
    header_height: int,
    padding: int,
    body_text: str = DEFAULT_LOCK_MESSAGE,
) -> int:
    """Giảm font body đến khi bounding box nằm trọn trong monitor."""

    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    smallest_size = 1
    low = smallest_size
    high = _font_size(region)
    best_size = smallest_size
    while low <= high:
        font_size = (low + high) // 2
        font = ImageFont.truetype(FONT_PATH, font_size)
        body = _wrap_text(draw, body_text, font, region.width - (padding * 2))
        bounds = draw.multiline_textbbox(
            (0, header_height + (font_size * 2)),
            body,
            font=font,
            spacing=font_size // 2,
        )
        if bounds[2] <= region.width - padding and bounds[3] <= region.height - padding:
            best_size = font_size
            low = font_size + 1
        else:
            high = font_size - 1
    return best_size


def _create_lock_image(
    region: screen_capture.ScreenRegion,
    header_text: str = DEFAULT_LOCK_HEADER,
    body_text: str = DEFAULT_LOCK_MESSAGE,
) -> Image.Image:
    """Dựng ảnh khóa responsive gồm header và body cho một monitor."""

    image = Image.new("RGB", (region.width, region.height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    body_font_size = _font_size(region)
    header_font_size = body_font_size
    header_font = ImageFont.truetype(FONT_PATH, header_font_size)
    padding = max(16, round(region.width * 0.012))
    while (
        draw.textbbox((0, 0), header_text, font=header_font)[2] > region.width - padding
        and header_font_size > 8
    ):
        header_font_size -= 1
        header_font = ImageFont.truetype(FONT_PATH, header_font_size)
    header_y = body_font_size // 3
    header_bottom = draw.textbbox((0, header_y), header_text, font=header_font)[3]
    header_gap = header_font_size
    separator_height = 20
    separator_y = header_bottom + header_gap + (separator_height // 2)
    body_top = header_bottom + header_gap + separator_height
    body_font_size = _fit_body_font_size(region, body_top, padding, body_text)
    body_font = ImageFont.truetype(FONT_PATH, body_font_size)
    draw.text(
        (0, header_y),
        header_text,
        font=header_font,
        fill=TEXT_COLOR,
    )
    draw.line(
        (0, separator_y, region.width, separator_y),
        fill=TEXT_COLOR,
        width=separator_height,
    )
    body = _wrap_text(draw, body_text, body_font, region.width - (padding * 2))
    draw.multiline_text(
        (0, body_top + (body_font_size * 2)),
        body,
        font=body_font,
        fill=TEXT_COLOR,
        spacing=body_font_size // 2,
    )
    return image


def _close_when_unlocked(
    root: tk.Tk,
    windows: list[tk.Tk | tk.Toplevel],
    stop_event: threading.Event,
) -> None:
    """Đóng overlay trên UI thread ngay khi `unlock()` gửi tín hiệu."""

    if not stop_event.is_set():
        root.after(100, _close_when_unlocked, root, windows, stop_event)
        return
    for window in reversed(windows):
        window.destroy()


def _create_windows(
    regions: list[screen_capture.ScreenRegion],
    header_text: str = DEFAULT_LOCK_HEADER,
    body_text: str = DEFAULT_LOCK_MESSAGE,
) -> tuple[tk.Tk, list[tk.Tk | tk.Toplevel]]:
    """Tạo một cửa sổ overlay cho từng monitor."""

    root = tk.Tk()
    windows: list[tk.Tk | tk.Toplevel] = [root]
    for index, region in enumerate(regions):
        window = root if index == 0 else tk.Toplevel(root)
        if window is not root:
            windows.append(window)
        ScreenLockOverlay(
            window,
            _create_lock_image(region, header_text, body_text),
            region,
        )
    return root, windows


def _run_ui(
    regions: list[screen_capture.ScreenRegion],
    ready_event: threading.Event,
    failed_event: threading.Event,
    stop_event: threading.Event,
    exited_event: threading.Event,
    header_text: str = DEFAULT_LOCK_HEADER,
    body_text: str = DEFAULT_LOCK_MESSAGE,
    cursor_operations: CursorOperations | None = None,
) -> None:
    """Tạo overlay và chạy Tk event loop trên UI thread."""

    global _ui_error

    operations = _input_operations or cast(InputBlockingOperations, input_blocker)
    input_blocked = False
    cursor_hidden = False
    try:
        root, windows = _create_windows(regions, header_text, body_text)
        operations.block()
        input_blocked = True
        if cursor_operations is not None:
            cursor_operations.hide_cursor()
            cursor_hidden = True
        ready_event.set()
        _close_when_unlocked(root, windows, stop_event)
        root.mainloop()
        if not stop_event.is_set():
            failed_event.set()
    except Exception as error:
        _ui_error = error
        failed_event.set()
        ready_event.set()
    finally:
        if cursor_hidden and cursor_operations is not None:
            try:
                cursor_operations.show_cursor()
            except Exception as error:
                _ui_error = error
                failed_event.set()
        if input_blocked:
            try:
                operations.unblock()
            except Exception as error:
                _ui_error = error
                failed_event.set()
        exited_event.set()


def _start_ui(
    regions: list[screen_capture.ScreenRegion],
    header_text: str,
    body_text: str,
    cursor_operations: CursorOperations,
) -> tuple[threading.Event, threading.Event, threading.Event, threading.Event]:
    """Khởi động UI thread và trả event báo trạng thái khởi tạo."""

    global _stop_event, _thread, _ui_exited_event, _ui_failed_event
    ready_event = threading.Event()
    failed_event = threading.Event()
    _stop_event = threading.Event()
    _ui_exited_event = threading.Event()
    _ui_failed_event = failed_event
    _thread = threading.Thread(
        target=_run_ui,
        args=(
            regions,
            ready_event,
            failed_event,
            _stop_event,
            _ui_exited_event,
            header_text,
            body_text,
            cursor_operations,
        ),
        daemon=True,
    )
    _thread.start()
    return ready_event, failed_event, _stop_event, _ui_exited_event


def _raise_after_lock_cleanup(
    error: Exception,
    lock_stop_event: threading.Event,
) -> NoReturn:
    """Dọn trạng thái lock dở dang trước khi báo lỗi ban đầu cho caller."""

    with _lock:
        if _stop_event is not lock_stop_event:
            raise error
        try:
            _unlock_locked()
        except Exception as cleanup_error:
            raise error from cleanup_error
    raise error


def lock(
    input_operations: InputBlockingOperations | None = None,
    *,
    cursor_operations: CursorOperations | None = None,
    header_text: str | None = None,
    body_text: str | None = None,
) -> None:
    """Phủ mọi monitor và chặn input sau khi overlay sẵn sàng."""

    with _lock:
        _lock_locked(
            input_operations,
            cursor_operations,
            header_text or DEFAULT_LOCK_HEADER,
            body_text or DEFAULT_LOCK_MESSAGE,
        )


def _lock_locked(
    input_operations: InputBlockingOperations | None = None,
    cursor_operations: CursorOperations | None = None,
    header_text: str = DEFAULT_LOCK_HEADER,
    body_text: str = DEFAULT_LOCK_MESSAGE,
) -> None:
    """Tạo và block đúng một locker khi caller đang giữ `_lock`."""

    global _input_operations, _stop_event, _thread, _ui_error
    if _thread is not None and _thread.is_alive():
        return
    operations = input_operations or cast(InputBlockingOperations, input_blocker)
    cursor = cursor_operations or get_default_platform_services().cursor_controller
    _input_operations = operations
    _ui_error = None
    regions = screen_capture.get_monitors()
    if not regions:
        raise RuntimeError("No monitors were found")
    ready_event, failed_event, stop_event, exited_event = _start_ui(
        regions,
        header_text,
        body_text,
        cursor,
    )

    if not ready_event.wait(timeout=5.0):
        _raise_after_lock_cleanup(
            RuntimeError("Screen locker UI did not start within 5 seconds"),
            stop_event,
        )
    if failed_event.is_set():
        _raise_after_lock_cleanup(
            _ui_error or RuntimeError("Screen locker UI failed to start"),
            stop_event,
        )
    if stop_event.is_set() or exited_event.is_set():
        _raise_after_lock_cleanup(
            RuntimeError("Screen locker UI stopped unexpectedly"),
            stop_event,
        )


def unlock() -> bool:
    """Mở input và xác nhận UI đã dọn xong, hoặc báo mọi lỗi cleanup."""

    with _lock:
        return _unlock_locked()


def _unlock_locked() -> bool:
    """Dọn đúng locker hiện tại khi caller đang giữ `_lock`."""

    global _input_operations

    stop_event = _stop_event
    exited_event = _ui_exited_event
    failed_event = _ui_failed_event
    ui_thread = _thread
    if stop_event is not None:
        stop_event.set()
    errors: list[Exception] = []
    if exited_event is None:
        if errors:
            raise errors[0]
        _input_operations = None
        return True
    if ui_thread is threading.current_thread():
        errors.append(RuntimeError("Cannot confirm UI cleanup from the UI thread"))
    elif not exited_event.wait(timeout=_UI_EXIT_TIMEOUT_SECONDS):
        errors.append(RuntimeError("Screen locker UI cleanup was not confirmed"))
    elif ui_thread is not None:
        ui_thread.join()
    if failed_event is not None and failed_event.is_set():
        errors.append(_ui_error or RuntimeError("Screen locker UI cleanup failed"))
    if len(errors) == 1:
        raise errors[0]
    if errors:
        raise ExceptionGroup("Screen locker unlock cleanup failed", errors)
    _input_operations = None
    return True


class ScreenLocker:
    """Owner của trạng thái screen lock và cleanup khi Runtime shutdown."""

    def __init__(
        self,
        input_operations: InputBlockingOperations | None = None,
        cursor_operations: CursorOperations | None = None,
    ) -> None:
        self._input_operations = input_operations
        self._cursor_operations = cursor_operations

    def lock(
        self,
        header_text: str | None = None,
        body_text: str | None = None,
    ) -> None:
        lock(
            self._input_operations,
            cursor_operations=self._cursor_operations,
            header_text=header_text,
            body_text=body_text,
        )

    def close(self) -> None:
        """Mở khóa và dọn toàn bộ trạng thái screen lock."""

        unlock()


__all__ = ["ScreenLocker"]
