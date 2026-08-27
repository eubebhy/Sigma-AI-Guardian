"""Lifecycle và command boundary trung tâm của SAG Agent.

File path: `src/agent/runtime/agent_runtime.py`.
Input: platform services, Agent config và registry tùy chọn cho test.
Output: Runtime start/shutdown idempotent và `execute()` trả response chuẩn hóa.
Nguyên lý: Runtime điều phối; FeatureManager sở hữu feature và CommandApi route allowlist.

Chạy demo học tập: `PYTHONPATH=src ./.pyvenv/bin/python src/agent/runtime/agent_runtime.py`.
"""

from agent.platform import PlatformServices, create_platform_services
from agent.runtime.command_api import CommandApi
from agent.runtime.feature_manager import FeatureManager
from agent.runtime.feature_registry import FeatureRegistry, create_default_registry
from agent.runtime.request_types import Request, Response
from config import AgentConfig


class AgentRuntime:
    """Owner cấp cao của config, platform services và feature lifecycle."""

    def __init__(
        self,
        services: PlatformServices,
        config: AgentConfig,
        registry: FeatureRegistry | None = None,
    ) -> None:

        self.services = services
        self.config = config
        self.features = FeatureManager(
            registry or create_default_registry(),
            services,
            config,
        )
        self._running = False
        self._closed = False
        self._commands = CommandApi(self.features, lambda: self._running)

    def start(self) -> None:
        if self._running:
            return

        if self._closed:
            raise RuntimeError("Agent Runtime is already closed")

        self.features.start_enabled()
        self._running = True

    def execute(self, request: Request) -> Response:
        if not self._running:
            raise RuntimeError("Agent Runtime is not running")
        return self._commands.execute(request)

    def shutdown(self) -> None:
        if self._closed:
            return
        try:
            self.features.shutdown()
        finally:
            self._running = False
            self._closed = True


def create_runtime(
    config: AgentConfig,
    platform_name: str | None = None,
) -> AgentRuntime:
    """Tạo Runtime với đúng một bộ platform adapter."""

    return AgentRuntime(create_platform_services(platform_name), config)


__all__ = ["AgentRuntime", "create_runtime"]
