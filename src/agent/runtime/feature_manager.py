"""Tạo và quản lý lifecycle feature của một SAG Agent Runtime.

File path: `src/agent/runtime/feature_manager.py`.
Input: registry, platform services và Agent config.
Output: instance feature theo tên và cleanup tập trung.
Nguyên lý: validate contract ngay sau factory; start một lần và shutdown theo thứ tự ngược.
"""

import logging

from agent.platform import PlatformServices
from agent.protocols import Resource, Service
from agent.runtime.feature_registry import FeatureRegistry
from config import AgentConfig


logger = logging.getLogger(__name__)


class FeatureManager:
    """Owner duy nhất của service và resource được Runtime tạo."""

    def __init__(
        self,
        registry: FeatureRegistry,
        services: PlatformServices,
        config: AgentConfig,
    ) -> None:
        self._registry = registry
        self._services = services
        self._config = config
        self._instances: dict[str, object] = {}
        self._creation_order: list[str] = []
        self._started = False
        self._closed = False

    def start_enabled(self) -> None:
        if self._started:
            return
        for definition in self._registry.definitions():
            if definition.enabled(self._config):
                self._create(definition.name)
        self._started = True

    def _create(self, name: str) -> object:
        definition = self._registry.get(name)
        instance = definition.factory(self._services, self._config)
        expected = Service if definition.kind == "service" else Resource
        if not isinstance(instance, expected):
            raise TypeError(f"Feature {name} must implement {expected.__name__}")
        if isinstance(instance, Service):
            instance.start()
        self._instances[name] = instance
        self._creation_order.append(name)
        logger.info("Started feature: %s", name)
        return instance

    def get(self, name: str) -> object:
        self._registry.get(name)
        try:
            return self._instances[name]
        except KeyError as error:
            raise RuntimeError(f"Feature is not enabled: {name}") from error

    def available_features(self) -> tuple[str, ...]:
        """Trả mọi feature Runtime biết cách tạo."""

        return self._registry.names()

    def active_features(self) -> tuple[str, ...]:
        """Trả feature đã được tạo theo thứ tự đăng ký."""

        return tuple(self._creation_order)

    def shutdown(self) -> None:
        if self._closed:
            return
        errors: list[Exception] = []
        for name in reversed(self._creation_order):
            instance = self._instances[name]
            try:
                if isinstance(instance, Service):
                    instance.stop()
                if isinstance(instance, Resource):
                    instance.close()
            except Exception as error:
                errors.append(error)
        self._closed = True
        if errors:
            raise ExceptionGroup("Feature shutdown failed", errors)


__all__ = ["FeatureManager"]
