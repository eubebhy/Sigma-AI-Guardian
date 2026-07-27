"""Kill process theo blacklist don gian.

File path: `src/device_controler/process_killer/__init__.py`
Input contract:
- ProcessKiller.blocked: danh sach exact process names can kill.
- set_blacklist(values): bo sung exact process names can kill.
- set_whitelist(values): exact process names khong duoc kill.
- start()/stop(): bat/tat vong quet nen.
Output contract:
- Process trung blacklist va khong nam trong whitelist se bi kill.
- Cac ham dieu khien khong tra ve gia tri.
Operating principle:
- Lay process theo OS hien tai.
- Chuan hoa process name ve lowercase.
- Background thread lap theo interval, match rule thi kill pid.
"""

from __future__ import annotations

import threading

from agent.contracts import ProcessOperations
from agent.platform import get_default_platform_services


class ProcessKiller:
    """Quét process nền và kill process nằm trong blacklist exact-name."""

    def __init__(self, process_operations: ProcessOperations | None = None) -> None:
        self.blocked: list[str] = []
        self.whitelist: set[str] | None = None
        self.running: bool = False
        self.interval: float = 0.67
        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        self._lifecycle_lock = threading.Lock()
        self._extra_exact: set[str] = set()
        self._process_operations = (
            process_operations or get_default_platform_services().processes
        )

    def set_whitelist(self, values: list[str] | None) -> None:
        """Đặt danh sách process name không được kill, hoặc xoá whitelist."""

        self.whitelist = {value.strip().lower() for value in values} if values else None

    def set_blacklist(self, values: list[str]) -> None:
        """Đặt blacklist bổ sung ngoài `blocked` mặc định của instance."""

        self._extra_exact = {value.strip().lower() for value in values}

    def start(self) -> None:
        """Bắt đầu daemon thread quét process nếu chưa chạy."""

        while True:
            with self._lifecycle_lock:
                thread = self._thread
                stop_event = self._stop_event
                if not thread or not thread.is_alive():
                    self.running = True
                    self._stop_event = threading.Event()
                    self._thread = threading.Thread(
                        target=self._run,
                        args=(self._stop_event,),
                        daemon=True,
                    )
                    self._thread.start()
                    return
                if stop_event and not stop_event.is_set():
                    return
            thread.join()

    def stop(self) -> None:
        """Dừng vòng quét nền ở lần lặp kế tiếp."""

        while True:
            with self._lifecycle_lock:
                self.running = False
                thread = self._thread
                if not thread:
                    return
                if self._stop_event:
                    self._stop_event.set()
            thread.join()
            with self._lifecycle_lock:
                if self._thread is thread:
                    self._thread = None
                    self._stop_event = None
                    return

    def _run(self, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            self._scan_and_kill()
            stop_event.wait(self.interval)

    def _scan_and_kill(self) -> None:
        for pid, name in self._process_operations.list_processes():
            if self._should_kill(name):
                try:
                    self._process_operations.kill_process(pid)
                except (PermissionError, ProcessLookupError):
                    # PID co the da thoat hoac khong du quyen; van quet PID sau.
                    continue

    def _should_kill(self, name: str) -> bool:
        if self.whitelist and name in self.whitelist:
            return False
        if name in set(self.blocked) | self._extra_exact:
            return True
        return False


__all__ = ["ProcessKiller"]
