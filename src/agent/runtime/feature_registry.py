# Dung StrEnum de tien lam key map / show list danh sach feature
from dataclasses import dataclass
from enum import auto, StrEnum
from typing import Callable, Any
from logging import getLogger

from config import AgentConfig
from agent.protocols import FeatureType
from agent.ipc_protocols import Command

logger = getLogger(__name__)


class FeatureName(StrEnum):
    SCREEN_LOCKER = auto()


@dataclass
# Cu phap python 3.12+; Hien tai ko co ke hoach dung ban cu hon
class FeatureDefinition[TFeature]:
    """Day la mot object dinh nghia mot Feature
    Cung cap cac thong tin giup phan loai feature, su dung"""

    feature_name: FeatureName
    feature_type: FeatureType
    enabled: Callable[[AgentConfig], bool]
    # Hàm dùng để tạo instance của Feature
    factory: Callable[[], TFeature]

    # Command -> method của Feature
    commands: dict[Command, Callable[[TFeature], None]]


# ===============================================================
# ==================== Phan feature registry ====================
# ===============================================================
class FeatureRegistry:
    """Chiu trach nhiem dang ki cac feature
    xac dinh dang co nhung feature nao, la service hay resource hay stateless
    factory de tao object
    cac command map voi api nao"""

    def __init__(self, _fea_defs: list[FeatureDefinition[object,]]):
        self.fea_defs: list[FeatureDefinition[object,]] = (
            _fea_defs or create_default_fea_def()
        )
        self._validate()

    def get_fea_def(self, feature_name: FeatureName) -> FeatureDefinition[Any,]:
        for fea_def in self.fea_defs:
            if fea_def.feature_name == feature_name:
                return fea_def

        raise KeyError(f"FeatureDefinition not found: {feature_name}")

    def get_all_fea_def(self) -> list[FeatureDefinition[Any,]]:
        if not self.fea_defs:
            logger.warning("Feature registry is empty")
        return self.fea_defs

    def _validate(self) -> None:
        """Kiem tra cac dau hieu dang ngo / tim nang loi ngam:
        - duplicate feature
        - duplicate command"""

        # Neu rong, khong loi nhung rat dang ngo
        if not self.fea_defs:
            logger.warning("Feature registry is empty!")
            return

        # Check duplicate command / feature_name
        registered_features: set[FeatureName] = set()
        registered_commands: set[Command] = set()

        for fea_def in self.fea_defs:
            # Check duplicate feature
            if fea_def.feature_name in registered_features:
                raise ValueError(f"Feature already registered: {fea_def.feature_name}")

            registered_features.add(fea_def.feature_name)

            # Check duplicate commands
            for command in fea_def.commands:
                if command in registered_commands:
                    raise ValueError(f"Command already registered: {command}")

                registered_commands.add(command)


def create_default_fea_def() -> list[FeatureDefinition[Any,]]:
    from device_controller.screen_locker import ScreenLocker

    return [
        FeatureDefinition[ScreenLocker,](
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
