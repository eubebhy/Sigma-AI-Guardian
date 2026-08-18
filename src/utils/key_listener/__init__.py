"""API lắng nghe input và đọc NumLock theo hệ điều hành.

File path: `src/utils/key_listener/__init__.py`.
Input: timeout chờ event, stop event tùy chọn hoặc lời gọi đọc trạng thái NumLock.
Output: generator keyboard/mouse event đã chuẩn hóa và trạng thái NumLock `bool`.
Nguyên lý: facade giữ public API cũ và lấy adapter mặc định từ Agent; dependency
native chỉ được nạp khi listener bắt đầu hoặc NumLock được đọc.
"""

from collections.abc import Iterator
import threading

from agent.platform_protocols import KeyListenerOperations
from agent.platform import get_default_platform_services
from utils.key_listener.types import KeyEvent, KeyState, MouseEvent, MouseState


def _get_operations() -> KeyListenerOperations:
    return get_default_platform_services().key_listener


def get_num_lock_state() -> bool:
    """Trả trạng thái NumLock từ adapter platform mặc định."""

    return _get_operations().get_num_lock_state()


def listen_keys(
    timeout: float | None = None,
    stop_event: threading.Event | None = None,
) -> Iterator[KeyEvent]:
    """Sinh keyboard event từ adapter platform mặc định."""

    return _get_operations().listen_keys(timeout, stop_event)


def listen_mice(
    timeout: float | None = None,
    stop_event: threading.Event | None = None,
) -> Iterator[MouseEvent]:
    """Sinh mouse event từ adapter platform mặc định."""

    return _get_operations().listen_mice(timeout, stop_event)


__all__ = [
    "KeyEvent",
    "KeyState",
    "MouseEvent",
    "MouseState",
    "get_num_lock_state",
    "listen_keys",
    "listen_mice",
]
