"""Lifecycle trung tâm của tiến trình SAG Agent.

File path: `src/agent/runtime.py`.
Input: `create_runtime()` nhận tên platform tùy chọn cho test.
Output: `AgentRuntime` cung cấp service OS cho entry point.
Nguyên lý: runtime tạo adapter đúng một lần và là owner của tài nguyên shutdown.
"""

from agent.platform import PlatformServices, create_platform_services
from agent.protocols import Service, Resource
from config import AgentConfig

from content_classifier import classifier
from device_controller.process_guard import process_guard
from device_controller.web_blocker import web_blocker
from device_controller.screen_locker import screen_locker

from dataclasses import dataclass
from logging import getLogger
import queue

logger = getLogger(__name__)
"""
Khong nen de AgentRuntime tu su ly PlatformServices va dependencies cho cac tinh nang.
Muc dinh la de de test, dependencies dong se de test hon.
"""


@dataclass(frozen=True)
class Request:
    id: str


class CommandRequest:
    object: str
    method: str
    kargs: str


class AgentRuntime:
    """Obj Agent su dung trong runtime, cung cap cac main API on dinh khong phan biet
    platform dang chay la gi.

    vi du: AgentRuntime(services=services)

    services: PlatformServices la obj cung cap adapter operations the feature su
    dung, no khong cung cap truc tiep logic cua feature.
    Time hieu them: src/agent/platform/__init__.py
    """

    def __init__(
        self,
        services: PlatformServices,
        config: AgentConfig,
    ) -> None:
        self.services = services
        self.config = config
        self._active_services: list[Service] = []
        self._resources: list[Resource] = []
        self._command_queue: queue.Queue[CommandRequest] = queue.Queue()

    def _register(self, component: object) -> None:
        """Chiu trach nhiem dang ki, tao resource, start service"""
        if isinstance(component, Service):
            component.start()
            self._active_services.append(component)
            logger.info(f"Started service: {type(component).__name__}")

        if isinstance(component, Resource):
            self._resources.append(component)
            logger.info(f"Created resource: {type(component).__name__}")

        if not isinstance(component, (Service, Resource)):
            raise RuntimeError(f"Unsupported component: {type(component).__name__}")

    def start_all_service_and_resource(self):
        """Chiu trach nhiem khoi dong cac dich vu va tai nguyen"""

        if self.config.process_guard.enabled:
            self._register(process_guard)

        if self.config.web_blocker.enabled:
            self._register(web_blocker)

        if self.config.classifier.enabled:
            self._register(classifier)

        if self.config.screen_lock.enabled:
            self._register(screen_locker)

    def start(self) -> None:
        self.start_all_service_and_resource()

    def shutdown(self) -> None:
        logger.info("Shutting down")
        errors: list[Exception] = []
        for service in self._active_services:
            try:
                service.stop()
                logger.info("Service %s stopped", type(service).__name__)
            except Exception as error:
                errors.append(error)

        for resource in self._resources:
            try:
                resource.close()
                logger.info("Resource %s closed", type(resource).__name__)
            except Exception as error:
                errors.append(error)

        if errors:
            raise ExceptionGroup("Agent shutdown failed", errors)


def create_runtime(
    config: AgentConfig,
    platform_name: str | None = None,
) -> AgentRuntime:
    """Tạo runtime Agent với adapter platform được chọn một lần."""

    return AgentRuntime(
        services=create_platform_services(platform_name),
        config=config,
    )
