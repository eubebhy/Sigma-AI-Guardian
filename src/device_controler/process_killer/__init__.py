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
import time

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

        if self._thread and self._thread.is_alive():
            return
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Dừng vòng quét nền ở lần lặp kế tiếp."""

        self.running = False

    def _run(self) -> None:
        while self.running:
            self._scan_and_kill()
            time.sleep(self.interval)

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
