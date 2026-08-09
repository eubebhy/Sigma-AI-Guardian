"""Lifecycle trung tâm của tiến trình SAG Agent.

File path: `src/agent/runtime.py`.
Input: `create_runtime()` nhận tên platform tùy chọn cho test.
Output: `AgentRuntime` cung cấp service OS cho entry point.
Nguyên lý: runtime tạo adapter đúng một lần và là owner của tài nguyên shutdown.
"""

from dataclasses import dataclass, field
from typing import cast

from agent.platform import PlatformServices, create_platform_services
from agent.protocols import Service, Resource
from logging import getLogger

logger = getLogger(__name__)
"""
Khong nen de AgentRuntime tu su ly PlatformServices va dependencies cho cac tinh nang.
Muc dinh la de de test, dependencies dong se de test hon.
"""


@dataclass
class AgentRuntime:
    """Obj Agent su dung trong runtime, cung cap cac main API on dinh khong phan biet
    platform dang chay la gi.

    vi du: AgentRuntime(services=services)

    services: PlatformServices la obj cung cap adapter operations the feature su
    dung, no khong cung cap truc tiep logic cua feature.
    Time hieu them: src/agent/platform/__init__.py
    """

    services: PlatformServices
    _active_services: list[Service]
    _resources: list[Resource]

    def shutdown(self):
        logger.info("Shutting down")
        for service in self._active_services:
            service.stop()
            logger.info("Service %s stopped", type(service).__name__)

        for resource in self._resources:
            resource.close()
            logger.info("Resource %s closed", type(resource).__name__)


def create_runtime(platform_name: str | None = None) -> AgentRuntime:
    """Tạo runtime Agent với adapter platform được chọn một lần."""

    return AgentRuntime(services=create_platform_services(platform_name))
