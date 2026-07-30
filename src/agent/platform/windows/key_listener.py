"""Adapter key listener Windows cho SAG Agent.

File path: `src/agent/platform/windows/key_listener.py`.
Input/Output: cung cấp keyboard, mouse, NumLock và cleanup theo contract Agent.
Nguyên lý: pynput/Win32 nằm trong backend; feature chỉ nhận event chuẩn hóa.
"""

from collections.abc import Iterator
import threading

from agent.contracts import KeyEvent, MouseEvent


_lifecycle_lock = threading.Lock()
_active_operations = 0


class WindowsKeyListenerOperations:
    """Chuyển operation Agent sang backend key listener Windows."""

    def __init__(self) -> None:
        self._active = False

    def _activate(self) -> None:
        global _active_operations

        with _lifecycle_lock:
            if not self._active:
                _active_operations += 1
                self._active = True

    def get_num_lock_state(self) -> bool:
        self._activate()
        from agent.platform.windows import key_listener_backend

        return key_listener_backend.get_num_lock_state()

    def listen_keys(self, timeout: float | None = None,
                    stop_event: threading.Event | None = None) -> Iterator[KeyEvent]:
        self._activate()
        from agent.platform.windows import key_listener_backend

        return key_listener_backend.listen_keys(timeout, stop_event)

    def listen_mice(self, timeout: float | None = None,
                    stop_event: threading.Event | None = None) -> Iterator[MouseEvent]:
        self._activate()
        from agent.platform.windows import key_listener_backend

        return key_listener_backend.listen_mice(timeout, stop_event)

    def close(self) -> None:
        """Không còn resource sau khi generator Windows kết thúc."""

        global _active_operations

        from agent.platform.windows import key_listener_backend

        with _lifecycle_lock:
            if not self._active:
                return
            _active_operations -= 1
            self._active = False
            should_close = _active_operations == 0
        if should_close:
            key_listener_backend.close()
