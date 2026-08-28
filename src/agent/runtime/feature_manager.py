"""Tạo và quản lý lifecycle feature của một SAG Agent Runtime.

File path: `src/agent/runtime/feature_manager.py`.
Input: registry, platform services và Agent config.
Output: instance feature theo tên và cleanup tập trung.
Nguyên lý: validate contract ngay sau factory; start một lần và shutdown theo thứ tự ngược.
"""

import logging
from typing import TypeVar

from agent.platform import PlatformServices
from agent.protocols import Resource, Service
from agent.runtime.feature_registry import FeatureInstance, FeatureRegistry
from agent.runtime.request_types import FeatureName
from config import AgentConfig


logger = logging.getLogger(__name__)
FeatureType = TypeVar("FeatureType", bound=FeatureInstance)


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
        self._instances: dict[FeatureName, FeatureInstance] = {}
        self._creation_order: list[FeatureName] = []
        self._started = False
        self._closed = False

    def start_enabled(self) -> None:
        if self._started:
            return

        for definition in self._registry.definitions():
            if definition.enabled(self._config):
                self._create(definition.name)

        self._started = True

    def _create(self, name: FeatureName) -> FeatureInstance:
        definition = self._registry.get(name)
        instance = definition.factory(self._services, self._config)
        if definition.kind == "service":
            if not isinstance(instance, Service):
                raise TypeError(f"Feature {name} must implement Service")
            instance.start()
        elif not isinstance(instance, Resource):
            raise TypeError(f"Feature {name} must implement Resource")

        self._instances[name] = instance
        self._creation_order.append(name)
        logger.info("Started feature: %s", name)

        return instance

    def get(self, name: FeatureName, expected_type: type[FeatureType]) -> FeatureType:
        self._registry.get(name)
        try:
            instance = self._instances[name]
        except KeyError as error:
            raise RuntimeError(f"Feature is not enabled: {name}") from error
        if not isinstance(instance, expected_type):
            raise TypeError(f"Feature {name} has an invalid type")
        return instance

    def available_features(self) -> tuple[FeatureName, ...]:
        """Trả mọi feature Runtime biết cách tạo."""

        return self._registry.names()

    def active_features(self) -> tuple[FeatureName, ...]:
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
