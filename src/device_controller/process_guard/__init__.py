"""Guard process theo blacklist don gian.

File path: `src/device_controller/process_guard/__init__.py`
Input contract:
- ProcessGuard.blocked: danh sach exact process names can kill.
- set_blacklist(values): bo sung exact process names can kill.
- set_whitelist(values): exact process names khong duoc kill.
- start()/stop(): bat/tat vong quet nen.
- raise_if_failed(): nem loi quet nen da luu, neu co.
Output contract:
- Process trung blacklist va khong nam trong whitelist se bi kill.
- Cac ham dieu khien khong tra ve gia tri; loi native duoc giu nguyen cho caller.
Operating principle:
- Lay process theo OS hien tai.
- Chuan hoa process name ve lowercase.
- Background thread lap theo interval, xac minh lai PID/name roi moi kill.
- Xac minh nay giam race PID reuse, nhung khong chung minh duoc identity OS bat bien
  khi process thay the van dung cung name.
- Daemon bo qua ProcessLookupError; loi quet/kill khac dung daemon va duoc luu de
  caller lay qua raise_if_failed().
"""

import logging
import threading

from agent.platform_protocols import ProcessOperations
from agent.platform import get_default_platform_services


logger = logging.getLogger(__name__)


class ProcessGuard:
    """Quét process nền và kill process nằm trong blacklist exact-name."""

    def __init__(self, process_operations: ProcessOperations | None = None) -> None:
        self.blocked: list[str] = []
        self.whitelist: set[str] | None = None
        self.running: bool = False
        self.interval: float = 0.67
        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        self._lifecycle_lock = threading.Lock()
        self._failure: Exception | None = None
        self._process_operations = (
            process_operations or get_default_platform_services().processes
        )

    def set_whitelist(self, values: list[str] | None) -> None:
        """Đặt danh sách process name không được kill, hoặc xoá whitelist."""

        self.whitelist = {value.strip().lower() for value in values} if values else None

    def set_blacklist(self, values: list[str]) -> None:
        """Đặt danh sách process bị chặn."""

        self.blocked = [value.strip().lower() for value in values]

    def start(self) -> None:
        """Bắt đầu daemon thread quét process nếu chưa chạy."""

        while True:
            with self._lifecycle_lock:
                thread = self._thread
                stop_event = self._stop_event
                if not thread or not thread.is_alive():
                    self.running = True
                    self._failure = None
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
                if thread is threading.current_thread():
                    self._thread = None
                    self._stop_event = None
                    return
            thread.join()
            with self._lifecycle_lock:
                if self._thread is thread:
                    self._thread = None
                    self._stop_event = None
                    return

    def raise_if_failed(self) -> None:
        """Ném lỗi quét nền gần nhất để caller xử lý bằng try/except."""

        with self._lifecycle_lock:
            failure = self._failure
        if failure is not None:
            raise failure

    def _run(self, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            try:
                self._scan_and_kill()
            except ProcessLookupError:
                logger.warning("Process exited while the process guard was scanning")
            except Exception as error:
                with self._lifecycle_lock:
                    self._failure = error
                return
            stop_event.wait(self.interval)

    def _scan_and_kill(self) -> None:
        for pid, name in self._process_operations.list_processes():
            normalized_name = name.strip().lower()

            if not self._should_kill(normalized_name):
                continue

            if not self._has_same_name(pid, normalized_name):
                continue

            try:
                self._process_operations.kill_process(pid)

            except ProcessLookupError:
                logger.warning(
                    "Process %s exited before the process guard could kill it",
                    pid,
                )
                continue

    def _has_same_name(self, pid: int, normalized_name: str) -> bool:
        """Xác minh PID/name ngay trước kill.

        Việc này giảm race do PID reuse nhưng không chứng minh identity OS bất biến
        khi process thay thế vẫn dùng cùng tên.
        """

        return any(
            current_pid == pid and name.strip().lower() == normalized_name
            for current_pid, name in self._process_operations.list_processes()
        )

    def _should_kill(self, name: str) -> bool:
        if self.whitelist and name in self.whitelist:
            return False

        if name in self.blocked:
            return True

        return False


process_guard = ProcessGuard()


__all__ = ["process_guard"]
