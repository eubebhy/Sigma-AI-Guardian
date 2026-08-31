from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Any
from logging import getLogger

from config import AgentConfig
from agent.protocols import Service, Resource, get_type, FeatureType

logger = getLogger(__name__)


class FeatureName(Enum):
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


@dataclass
class FeatureManager:
    act_services: dict[FeatureName, Service]
    act_resources: dict[FeatureName, Resource]
    config: AgentConfig
    fea_reg: FeatureRegistry

    def start_enabled(self):
        for fea_def in self.fea_reg.get_all_fea_def():
            if not fea_def.enabled(self.config):
                continue

            instance = fea_def.factory()

            detected_type = get_type(instance)

            if not isinstance(detected_type, instance.feature_type):
                raise RuntimeError(
                    "Declared feature type does not match detected type."
                )

            if instance.feature_type == FeatureType.SERVICE:
                self.act_services[fea_def.feature_name] = instance

            elif instance.feature_type == FeatureType.RESOURCE:
                self.act_resources[fea_def.feature_name] = instance

    def shutdown_all(self):
        for name, serv in self.act_services.items():
            serv.stop()
            logger.info(f"Stopped {name} service")

        self.act_services.clear()
        logger.info("All services stopped successfully")

        for name, resource in self.act_resources.items():
            resource.close()
            logger.info(f"Released {name} resource")

        self.act_resources.clear()
        logger.info("All resource Released successfully")
