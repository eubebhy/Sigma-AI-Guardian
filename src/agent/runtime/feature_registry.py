"""Danh mục tường minh các feature do SAG Agent Runtime quản lý.

File path: `src/agent/runtime/feature_registry.py`.
Input: tên, loại lifecycle, factory và điều kiện enable của feature.
Output: `FeatureRegistry` tra cứu definition ổn định theo tên.
Nguyên lý: không scan package hoặc dựa vào import side effect; mọi feature phải đăng ký.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent.platform import PlatformServices
from config import AgentConfig


FeatureKind = Literal["service", "resource"]
FeatureFactory = Callable[[PlatformServices, AgentConfig], object]
FeatureEnabled = Callable[[AgentConfig], bool]


def _always_enabled(_config: AgentConfig) -> bool:
    return True


@dataclass(frozen=True)
class FeatureDefinition:
    """Khai báo cách Runtime tạo và quản lý một feature."""

    name: str
    kind: FeatureKind
    factory: FeatureFactory
    enabled: FeatureEnabled = _always_enabled


class FeatureRegistry:
    """Danh mục feature không trùng tên và không tự discovery."""

    def __init__(self, definitions: Iterable[FeatureDefinition]) -> None:
        self._definitions: dict[str, FeatureDefinition] = {}
        for definition in definitions:
            if definition.name in self._definitions:
                raise ValueError(f"Duplicate feature: {definition.name}")
            self._definitions[definition.name] = definition

    def definitions(self) -> tuple[FeatureDefinition, ...]:
        return tuple(self._definitions.values())

    def names(self, kind: FeatureKind | None = None) -> tuple[str, ...]:
        """Trả tên feature đã đăng ký, có thể lọc theo lifecycle type."""

        return tuple(
            definition.name
            for definition in self._definitions.values()
            if kind is None or definition.kind == kind
        )

    def get(self, name: str) -> FeatureDefinition:
        try:
            return self._definitions[name]
        except KeyError as error:
            raise KeyError(f"Unknown feature: {name}") from error


def _create_process_guard(services: PlatformServices, config: AgentConfig) -> object:
    from device_controller.process_guard import ProcessGuard

    guard = ProcessGuard(services.processes)
    guard.interval = config.process_guard.scan_interval_seconds
    guard.set_whitelist(config.process_guard.custom_allowlist)
    guard.set_blacklist(config.process_guard.custom_blocklist)
    return guard


def _create_web_blocker(services: PlatformServices, _config: AgentConfig) -> object:
    from device_controller.web_blocker import WebBlocker

    return WebBlocker(hosts_path=Path(services.hosts.get_hosts_path()))


def _create_classifier(_services: PlatformServices, _config: AgentConfig) -> object:
    from content_classifier import Classifier

    return Classifier()


def _create_screen_locker(services: PlatformServices, _config: AgentConfig) -> object:
    from device_controller.screen_locker import ScreenLocker

    return ScreenLocker(services.input_blocker, services.cursor_controller)


def create_default_registry() -> FeatureRegistry:
    """Tạo danh mục feature low-level hiện được Agent Runtime sở hữu."""

    return FeatureRegistry(
        (
            FeatureDefinition(
                "process_guard",
                "service",
                _create_process_guard,
                lambda config: config.process_guard.enabled,
            ),
            FeatureDefinition(
                "web_blocker",
                "resource",
                _create_web_blocker,
                lambda config: config.web_blocker.enabled,
            ),
            FeatureDefinition(
                "classifier",
                "resource",
                _create_classifier,
                lambda config: config.classifier.enabled,
            ),
            FeatureDefinition(
                "screen_locker",
                "resource",
                _create_screen_locker,
                lambda config: config.screen_lock.enabled,
            ),
        )
    )


__all__ = ["FeatureDefinition", "FeatureRegistry", "create_default_registry"]
