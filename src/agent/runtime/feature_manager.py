from dataclasses import dataclass
from enum import Enum, auto, StrEnum
from typing import Callable, Any
from logging import getLogger

from config import AgentConfig
from agent.protocols import Service, Resource, get_type, FeatureType

logger = getLogger(__name__)


# Dung StrEnum de tien lam key map / show list danh sach feature
class FeatureName(StrEnum):
    SCREEN_LOCKER = auto()


class Command(Enum):
    LOCK_SCREEN = auto()
    UNLOCK_SCREEN = auto()


@dataclass
# Cu phap python 3.12+; Hien tai ko co ke hoach dung ban cu hon
class FeatureDefinition[TFeature, TConfig]:
    """Day la mot object dinh nghia mot Feature
    Cung cap cac thong tin giup phan loai feature, su dung"""

    feature_name: FeatureName
    feature_type: FeatureType
    enabled: Callable[[TConfig], bool]
    # Hàm dùng để tạo instance của Feature
    factory: Callable[[], TFeature]

    # Command -> method của Feature
    commands: dict[Command, Callable[[TFeature], None]]


class FeatureRegistry:
    """Chiu trach nhiem dang ki cac feature
    xac dinh dang co nhung feature nao, la service hay resource hay stateless
    factory de tao object
    cac command map voi api nao"""

    def __init__(self, _fea_defs: list[FeatureDefinition[object, AgentConfig]]):
        self.fea_defs: list[FeatureDefinition[object, AgentConfig]] = (
            _fea_defs or create_default_fea_def()
        )

    def get_fea_def(
        self, feature_name: FeatureName
    ) -> FeatureDefinition[Any, AgentConfig]:
        for fea_def in self.fea_defs:
            if fea_def.feature_name == feature_name:
                return fea_def

        raise KeyError(f"FeatureDefinition not found: {feature_name}")

    def get_all_fea_def(self) -> list[FeatureDefinition[Any, AgentConfig]]:
        if not self.fea_defs:
            logger.warning("Feature registry is empty")
        return self.fea_defs


def create_default_fea_def() -> list[FeatureDefinition[Any, AgentConfig]]:
    from device_controller.screen_locker import ScreenLocker

    return [
        FeatureDefinition[ScreenLocker, AgentConfig](
            feature_name=FeatureName.SCREEN_LOCKER,
            feature_type=FeatureType.RESOURCE,
            enabled=lambda config: config.screen_lock.enabled,
            factory=ScreenLocker,
            commands={
                Command.LOCK_SCREEN: ScreenLocker.lock,
                Command.UNLOCK_SCREEN: ScreenLocker.close,
            },
        )
    ]


def _format_unknown_feature(
    feature_name: FeatureName,
    services: dict[FeatureName, Service],
    resources: dict[FeatureName, Resource],
) -> str:
    services_text = ", ".join(name.name for name in services)
    resources_text = ", ".join(name.name for name in resources)

    return (
        f"Unknown feature: {feature_name.name}; "
        f"available services: [{services_text}]; "
        f"available resources: [{resources_text}]"
    )


@dataclass
class FeatureManager:
    act_services: dict[FeatureName, Service]
    act_resources: dict[FeatureName, Resource]
    config: AgentConfig
    fea_reg: FeatureRegistry

    def start_enabled(self) -> None:
        self._start_enabled_services()
        self._start_enabled_resources()

    def sync(self) -> None:
        """Synchronize active features with the current configuration."""
        self._stop_disabled_services()
        self._stop_disabled_resources()
        self._start_enabled_services()
        self._start_enabled_resources()

    def shutdown_all(self) -> None:
        for name, service in self.act_services.items():
            service.stop()
            logger.info("Stopped %s service", name)

        self.act_services.clear()
        logger.info("All services stopped successfully")

        for name, resource in self.act_resources.items():
            resource.close()
            logger.info("Released %s resource", name)

        self.act_resources.clear()
        logger.info("All resources released successfully")

    def get_fea(self, feature_name: FeatureName) -> Service | Resource:
        service = self.act_services.get(feature_name)
        if service is not None:
            return service

        resource = self.act_resources.get(feature_name)
        if resource is not None:
            return resource

        raise KeyError(
            _format_unknown_feature(
                feature_name,
                self.act_services,
                self.act_resources,
            )
        )

    def _start_enabled_services(self) -> None:
        for fea_def in self.fea_reg.get_all_fea_def():
            if fea_def.feature_type != FeatureType.SERVICE:
                continue

            if not fea_def.enabled(self.config):
                continue

            if fea_def.feature_name in self.act_services:
                continue

            instance = self._create_feature(fea_def)
            instance.start()

            self.act_services[fea_def.feature_name] = instance
            logger.info("Started %s service", fea_def.feature_name)

    def _start_enabled_resources(self) -> None:
        for fea_def in self.fea_reg.get_all_fea_def():
            if fea_def.feature_type != FeatureType.RESOURCE:
                continue

            if not fea_def.enabled(self.config):
                continue

            if fea_def.feature_name in self.act_resources:
                continue

            instance = self._create_feature(fea_def)

            self.act_resources[fea_def.feature_name] = instance
            logger.info("Allocated %s resource", fea_def.feature_name)

    def _stop_disabled_services(self) -> None:
        for name, service in list(self.act_services.items()):
            fea_def = self.fea_reg.get_fea_def(name)

            if fea_def.enabled(self.config):
                continue

            service.stop()
            del self.act_services[name]

            logger.info("Stopped %s service", name)

    def _stop_disabled_resources(self) -> None:
        for name, resource in list(self.act_resources.items()):
            fea_def = self.fea_reg.get_fea_def(name)

            if fea_def.enabled(self.config):
                continue

            resource.close()
            del self.act_resources[name]

            logger.info("Released %s resource", name)

    def _create_feature(
        self,
        fea_def: FeatureDefinition[Any, AgentConfig],
    ) -> Any:
        instance = fea_def.factory()

        detected_type = get_type(instance)

        if detected_type != fea_def.feature_type:
            raise RuntimeError("Declared feature type does not match detected type.")

        return instance
