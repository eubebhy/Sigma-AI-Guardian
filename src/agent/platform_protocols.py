"""Protocol platform giữa feature SAG Agent và adapter hệ điều hành.

File path: `src/agent/platform_protocols.py`.
Input: adapter cung cấp process, browser, window, hosts và input theo protocol ở đây.
Output: feature nhận dữ liệu chuẩn hóa, không phụ thuộc lệnh native từng OS.
Nguyên lý: contract chỉ mô tả capability nhỏ; nó không import adapter hay feature.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
import threading
from typing import Callable, Literal, Protocol, TypeAlias


Key: TypeAlias = str
MouseButton: TypeAlias = Literal[
    "primary",
    "secondary",
    "left",
    "right",
    "middle",
    "forward",
    "back",
]
KeyState: TypeAlias = Literal["down", "up", "hold"]
KeyEvent: TypeAlias = tuple[str, KeyState]
MouseState: TypeAlias = Literal["down", "up"]
MouseButtonEvent: TypeAlias = tuple[str, MouseState]
MouseMoveEvent: TypeAlias = tuple[str, int]
MouseEvent: TypeAlias = MouseButtonEvent | MouseMoveEvent


class ProcessOperations(Protocol):
    """Liệt kê và kết thúc process theo format Agent thống nhất."""

    def list_processes(self) -> list[tuple[int, str]]:
        """Trả `(pid, process_name_lowercase)`; lỗi native được giữ nguyên."""

        ...

    def kill_process(self, pid: int) -> None:
        """Yêu cầu hệ điều hành kết thúc process theo PID và giữ nguyên lỗi native."""

        ...


class CursorOperations(Protocol):
    """An va hien cursor, dung trong screen locker"""

    def show_cursor(self) -> None: ...

    def hide_cursor(self) -> None: ...


class BrowserOperations(Protocol):
    """Khởi chạy browser mà không chặn Agent process."""

    def launch(self, command: list[str]) -> bool:
        """Trả `True` khi process browser được tạo thành công."""

        ...

    def open_default_url(self, url: str) -> bool:
        """Yêu cầu browser mặc định của platform mở URL hợp lệ."""

        ...

    def find_executable(self, executables: tuple[str, ...]) -> str | None:
        """Trả executable browser đầu tiên có thể chạy trên platform."""

        ...


class WindowOperations(Protocol):
    """Đọc title và process name của desktop hiện tại."""

    def get_active_window(self) -> tuple[str, str]:
        """Trả `(title, process_name)`, hoặc hai chuỗi rỗng nếu không có."""

        ...

    def get_open_windows(self) -> dict[str, str]:
        """Trả mapping title sang process name của cửa sổ đang mở."""

        ...


class HostsPathOperations(Protocol):
    """Cung cấp đường dẫn hosts của hệ điều hành hiện tại."""

    def get_hosts_path(self) -> Path:
        """Trả đường dẫn hosts chuẩn của platform."""

        ...


class InputBlockingOperations(Protocol):
    """Chặn và mở chặn input vật lý trên desktop hiện tại."""

    def block(self) -> None:
        """Chặn keyboard và mouse, hoặc raise lỗi native."""
        ...

    def unblock(self) -> None:
        """Mở chặn keyboard và mouse, hoặc raise lỗi cleanup."""
        ...

    def close(self) -> None:
        """Dọn trạng thái block còn thuộc adapter này."""
        ...


class KeyListenerOperations(Protocol):
    """Đọc input vật lý và trạng thái NumLock theo format Agent."""

    def get_num_lock_state(self) -> bool:
        """Trả trạng thái NumLock hiện tại."""
        ...

    def listen_keys(
        self,
        timeout: float | None = None,
        stop_event: threading.Event | None = None,
    ) -> Iterator[KeyEvent]:
        """Sinh keyboard event đã chuẩn hóa."""
        ...

    def listen_mice(
        self,
        timeout: float | None = None,
        stop_event: threading.Event | None = None,
    ) -> Iterator[MouseEvent]:
        """Sinh mouse event đã chuẩn hóa."""
        ...

    def close(self) -> None:
        """Đóng resource listener được adapter cache."""
        ...


class InputControllerOperations(Protocol):
    """Gửi keyboard và mouse event theo public API chung."""

    _closed: bool

    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: MouseButton = "primary",
    ) -> None: ...

    def keyDown(self, key: str) -> None: ...

    def keyUp(self, key: str) -> None: ...

    def mouseDown(self, button: MouseButton) -> None: ...

    def mouseUp(self, button: MouseButton) -> None: ...

    def moveRel(self, x: int | None, y: int | None, duration: float = 0.0) -> None: ...

    def moveTo(self, x: int | None, y: int | None, duration: float = 0.0) -> None: ...

    def position(self, take_new: bool = False) -> tuple[int, int]: ...

    def press(self, keys: str | Sequence[str]) -> None: ...

    def scroll(self, amount: int) -> None: ...

    def sideScroll(self, amount: int) -> None: ...

    def supportedKeys(self) -> tuple[str, ...]: ...

    def supportedWriteCharacters(self) -> str: ...

    def write(self, message: str, interval: float = 0.0) -> None: ...

    def close(self) -> None:
        """Đóng virtual device và connection được adapter cache.
        Linux ONLY"""
        ...

    def create(self) -> None:
        """Tao UInput device ben Linux"""
        ...
