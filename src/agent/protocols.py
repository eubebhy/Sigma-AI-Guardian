"""Protocol lifecycle chung cho service và resource của SAG Agent."""

from typing import Protocol


class Service(Protocol):
    """Đối tượng có lifecycle start/stop do AgentRuntime quản lý."""

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...


class Resource(Protocol):
    """Đối tượng giữ resource cần được đóng khi AgentRuntime shutdown."""

    def close(self) -> None:
        ...


__all__ = ["Resource", "Service"]
