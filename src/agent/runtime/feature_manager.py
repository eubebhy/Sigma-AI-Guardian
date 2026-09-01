from logging import getLogger
from typing import Any


from config import AgentConfig
from agent.protocols import Service, Resource, get_type, FeatureType
from agent.runtime.feature_registry import (
    FeatureName,
    FeatureRegistry,
    FeatureDefinition,
)

logger = getLogger(__name__)
"""
Giai thich nhanh logic hoat dong

[FeatureRegistry]
FeatureRegistry dung nhu cai ten cua no, no chiu trach nhiem dang ki cac feature
mot feature se duoc dang ki va dai dien bang FeatureDefinition.
Cac FeatureDefinition se co cac thuoc tinh dac trung va type safe
=> Noi cach khac, FeatureRegistry = bang dang ki / khai bao cac feature


[FeatureManager]
Thu nay chiu trach nhiem quan ly cac feature. Vi du nhu bat, tat.
Cung cap API tien loi de quan ly life cycle cua feature mot cach sach se
FeatureManager phu thuoc vao FeatureRegustry.
=> Tom lai, FeatureManager dung "ban dang ki" FeatureRegistry de tao va quan ly
life cycle cua feature

"""


# ===============================================================
# ========================= Phan feature manager ================
# ===============================================================
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


class FeatureManager:
    def __init__(self, config: AgentConfig, fea_reg: FeatureRegistry) -> None:
        self.config: AgentConfig = config
        self.fea_reg: FeatureRegistry = fea_reg

    act_services: dict[FeatureName, Service]
    act_resources: dict[FeatureName, Resource]

    def start_enabled(self) -> None:
        logger.info("Starting all enabled feature")
        self._start_enabled_services()
        self._start_enabled_resources()

    def sync(self) -> None:
        """Synchronize active features with the current configuration."""
        logger.info("Syncing features with current configuration")
        self._stop_disabled_services()
        self._stop_disabled_resources()
        self._start_enabled_services()
        self._start_enabled_resources()

    def shutdown_all(self) -> None:
        logger.info("Shuting down all feature")
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
        fea_def: FeatureDefinition[Any,],
    ) -> Any:
        instance = fea_def.factory()

        detected_type = get_type(instance)

        if detected_type != fea_def.feature_type:
            raise RuntimeError("Declared feature type does not match detected type.")

        return instance
