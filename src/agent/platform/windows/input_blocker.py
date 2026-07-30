"""Adapter chặn input Windows cho SAG Agent.

File path: `src/agent/platform/windows/input_blocker.py`.
Input/Output: triển khai block, unblock và cleanup theo contract Agent.
Nguyên lý: giữ trạng thái ownership; native `BlockInput` nằm trong backend platform.
"""

import threading


_lock = threading.RLock()
_block_count = 0
_owner_thread_id: int | None = None


class WindowsInputBlockingOperations:
    """Chuyển operation Agent sang backend input blocker Windows."""

    def __init__(self) -> None:
        self._blocked = False

    def block(self) -> None:
        global _block_count, _owner_thread_id

        from agent.platform.windows import input_blocker_backend

        with _lock:
            if self._blocked:
                return
            thread_id = threading.get_ident()
            if _owner_thread_id is not None and _owner_thread_id != thread_id:
                raise RuntimeError("Windows input blocker belongs to another thread")
            if _block_count == 0:
                input_blocker_backend.block()
                _owner_thread_id = thread_id
            _block_count += 1
            self._blocked = True

    def unblock(self) -> None:
        global _block_count, _owner_thread_id

        from agent.platform.windows import input_blocker_backend

        with _lock:
            if not self._blocked:
                return
            if _owner_thread_id != threading.get_ident():
                raise RuntimeError("Windows input must be unblocked by its owner thread")
            _block_count -= 1
            if _block_count == 0:
                try:
                    input_blocker_backend.unblock()
                except Exception:
                    _block_count += 1
                    raise
                _owner_thread_id = None
            self._blocked = False

    def close(self) -> None:
        """Mở chặn nếu adapter này đã block input thành công."""

        if self._blocked:
            self.unblock()
