"""Lifecycle trung tâm của tiến trình SAG Agent.

File path: `src/agent/runtime.py`.
Input: `create_runtime()` nhận tên platform tùy chọn cho test.
Output: `AgentRuntime` cung cấp service OS và `status()` cho entry point.
Nguyên lý: runtime tạo adapter đúng một lần và là owner của tài nguyên shutdown.
"""

from dataclasses import dataclass

from agent.platform import PlatformServices, create_platform_services


@dataclass
class AgentRuntime:
    """Runtime cục bộ có adapter platform dùng chung cho các feature."""

    services: PlatformServices

    def status(self) -> str:
        """Trả capability status của Agent mà không đụng desktop thật."""

        return self.services.capabilities.format_status()

    def shutdown(self) -> None:
        """Kết thúc runtime; feature hiện có tự quản lý lifecycle của chúng."""


def create_runtime(platform_name: str | None = None) -> AgentRuntime:
    """Tạo runtime Agent với adapter platform được chọn một lần."""

    return AgentRuntime(services=create_platform_services(platform_name))
