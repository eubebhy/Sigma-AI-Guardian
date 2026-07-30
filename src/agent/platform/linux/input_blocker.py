"""Adapter chặn input Linux cho SAG Agent.

File path: `src/agent/platform/linux/input_blocker.py`.
Input/Output: triển khai `InputBlockingOperations` bằng backend evdev hiện có.
Nguyên lý: adapter giữ platform selection ngoài feature và bảo toàn lifecycle grab.
"""

import threading


_lock = threading.RLock()
_block_count = 0


class LinuxInputBlockingOperations:
    """Chuyển operation Agent sang backend input blocker Linux."""

    def __init__(self) -> None:
        self._blocked = False

    def block(self) -> None:
        global _block_count

        from agent.platform.linux import input_blocker_backend

        with _lock:
            if self._blocked:
                return
            if _block_count == 0:
                input_blocker_backend.block()
            _block_count += 1
            self._blocked = True

    def unblock(self) -> None:
        global _block_count

        from agent.platform.linux import input_blocker_backend

        with _lock:
            if not self._blocked:
                return
            _block_count -= 1
            if _block_count == 0:
                try:
                    input_blocker_backend.unblock()
                except Exception:
                    _block_count += 1
                    raise
            self._blocked = False

    def close(self) -> None:
        """Mở chặn nếu adapter này đã block input thành công."""

        if self._blocked:
            self.unblock()
