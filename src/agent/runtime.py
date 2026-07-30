"""Lifecycle trung tâm của tiến trình SAG Agent.

File path: `src/agent/runtime.py`.
Input: `create_runtime()` nhận tên platform tùy chọn cho test.
Output: `AgentRuntime` cung cấp service OS và `status()` cho entry point.
Nguyên lý: runtime tạo adapter đúng một lần và là owner của tài nguyên shutdown.
"""

from dataclasses import dataclass, field
import threading

from agent.platform import PlatformServices, create_platform_services

"""
Khong nen de AgentRuntime tu su ly PlatformServices va dependencies cho cac tinh nang.
Muc dinh la de de test, dependencies dong se de test hon.
"""


@dataclass
class AgentRuntime:
    """Obj Agent su dung trong runtime, cung cap cac main API on dinh khong phan biet
    platform dang chay la gi.

    vi du: Agent.status()

    services: PlatformServices la obj cung cap adapter operations the feature su
    dung, no khong cung cap truc tiep logic cua feature.
    Time hieu them: src/agent/platform/__init__.py
    """

    services: PlatformServices
    _closed: bool = field(default=False, init=False)
    _shutdown_lock: threading.Lock = field(
        default_factory=threading.Lock,
        init=False,
    )

    def status(self) -> str:
        """Trả capability status của Agent mà không đụng desktop thật."""

        return self.services.capabilities.format_status()

    def shutdown(self) -> None:
        """Đóng resource platform do runtime sở hữu."""

        with self._shutdown_lock:
            if self._closed:
                return
            errors: list[Exception] = []
            for operations in (
                self.services.input_controller,
                self.services.key_listener,
                self.services.input_blocker,
            ):
                try:
                    operations.close()
                except Exception as error:
                    errors.append(error)
            if errors:
                raise ExceptionGroup("Agent runtime cleanup failed", errors)
            self._closed = True


def create_runtime(platform_name: str | None = None) -> AgentRuntime:
    """Tạo runtime Agent với adapter platform được chọn một lần."""

    return AgentRuntime(services=create_platform_services(platform_name))
