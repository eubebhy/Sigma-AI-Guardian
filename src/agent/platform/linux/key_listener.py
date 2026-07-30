"""Adapter key listener Linux cho SAG Agent.

File path: `src/agent/platform/linux/key_listener.py`.
Input/Output: đọc keyboard, mouse và NumLock qua backend Linux hiện có.
Nguyên lý: adapter cung cấp contract Agent; evdev/X11 vẫn nằm sau boundary platform.
"""

from collections.abc import Iterator
import threading

from agent.contracts import KeyEvent, MouseEvent


_lifecycle_lock = threading.Lock()
_active_operations = 0


class LinuxKeyListenerOperations:
    """Chuyển operation Agent sang backend key listener Linux."""

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
        from agent.platform.linux import key_listener_backend

        return key_listener_backend.get_num_lock_state()

    def listen_keys(
        self,
        timeout: float | None = None,
        stop_event: threading.Event | None = None,
    ) -> Iterator[KeyEvent]:
        self._activate()
        from agent.platform.linux import key_listener_backend

        return key_listener_backend.listen_keys(timeout, stop_event)

    def listen_mice(
        self,
        timeout: float | None = None,
        stop_event: threading.Event | None = None,
    ) -> Iterator[MouseEvent]:
        self._activate()
        from agent.platform.linux import key_listener_backend

        return key_listener_backend.listen_mice(timeout, stop_event)

    def close(self) -> None:
        """Đóng input device Linux đã cache."""

        global _active_operations

        from agent.platform.linux import key_listener_backend

        with _lifecycle_lock:
            if not self._active:
                return
            _active_operations -= 1
            self._active = False
            should_close = _active_operations == 0
        if should_close:
            key_listener_backend.close()
