"""Đăng ký và thực thi command của SAG Agent Runtime.

File path: `src/agent/runtime/command_api.py`.
Input: `Request` có `CommandName` đã được transport decode.
Output: `Response` chứa trạng thái và dữ liệu của command.
Nguyên lý: command stateful khai báo feature, feature type và handler tại một nơi;
stateless command không phụ thuộc FeatureRegistry.
"""

from collections.abc import Callable
from dataclasses import dataclass

from agent.runtime.feature_manager import FeatureManager
from agent.runtime.feature_registry import FeatureInstance
from agent.runtime.request_types import (
    AgentState,
    AgentStatus,
    CommandName,
    FeatureName,
    Request,
    RequestStatus,
    Response,
)
from device_controller.screen_locker import ScreenLocker


CommandData = AgentStatus | None
CommandHandler = Callable[[Request], CommandData]


@dataclass(frozen=True)
class CommandDefinition:
    """Khai báo một command và dependency Runtime của nó."""

    feature: FeatureName | None
    feature_type: type[FeatureInstance] | None
    handler: CommandHandler


class CommandApi:
    """Route command được phép tới feature do Runtime sở hữu."""

    def __init__(
        self,
        features: FeatureManager,
        is_running: Callable[[], bool],
    ) -> None:
        self._features = features
        self._is_running = is_running
        self._commands = self._create_command_definitions()
        self._validate_definitions()

    def _create_command_definitions(self) -> dict[CommandName, CommandDefinition]:
        """Khai báo command, feature phụ thuộc và handler tại một nơi."""

        return {
            # Stateless Runtime API
            CommandName.GET_AGENT_STATUS: CommandDefinition(
                feature=None,
                feature_type=None,
                handler=self._get_agent_status,
            ),
            # ScreenLocker resource API
            CommandName.LOCK_SCREEN: CommandDefinition(
                feature=FeatureName.SCREEN_LOCKER,
                feature_type=ScreenLocker,
                handler=self._lock_screen,
            ),
            CommandName.UNLOCK_SCREEN: CommandDefinition(
                feature=FeatureName.SCREEN_LOCKER,
                feature_type=ScreenLocker,
                handler=self._unlock_screen,
            ),
        }

    def _validate_definitions(self) -> None:
        if set(self._commands) != set(CommandName):
            raise RuntimeError("Command definitions do not match CommandName")
        available_features = set(self._features.available_features())
        for definition in self._commands.values():
            self._validate_definition(definition, available_features)

    def _validate_definition(
        self,
        definition: CommandDefinition,
        available_features: set[FeatureName],
    ) -> None:
        if definition.feature is None and definition.feature_type is not None:
            raise RuntimeError("Stateless command must not define a feature type")
        if definition.feature is not None and definition.feature_type is None:
            raise RuntimeError("Stateful command must define a feature type")
        if definition.feature is not None and definition.feature not in available_features:
            raise RuntimeError(
                f"Command feature is not registered: {definition.feature}"
            )

    def execute(self, request: Request) -> Response:
        definition = self._commands[request.command]
        if definition.feature is not None:
            return self._execute_feature_command(request, definition)
        return self._execute_handler(request, definition.handler)

    def _execute_feature_command(
        self,
        request: Request,
        definition: CommandDefinition,
    ) -> Response:
        feature = definition.feature
        if feature is None:
            raise RuntimeError("Stateful command does not define a feature")
        if feature not in self._features.active_features():
            return Response(
                request.id,
                RequestStatus.REJECTED,
                reason=f"Required feature is not enabled: {feature}",
                error_code="feature_not_enabled",
            )
        if definition.feature_type is None:
            raise RuntimeError("Stateful command does not define a feature type")
        self._features.get(feature, definition.feature_type)
        return self._execute_handler(request, definition.handler)

    def _execute_handler(self, request: Request, handler: CommandHandler) -> Response:
        try:
            return Response(request.id, RequestStatus.SUCCEEDED, handler(request))
        except Exception as error:
            return Response(
                request.id,
                RequestStatus.FAILED,
                reason=str(error),
                error_code="command_failed",
            )

    def _get_agent_status(self, _request: Request) -> AgentStatus:
        state = AgentState.RUNNING if self._is_running() else AgentState.STOPPED
        return AgentStatus(state, self._features.active_features())

    def _lock_screen(self, _request: Request) -> None:
        self._get_screen_locker().lock()

    def _unlock_screen(self, _request: Request) -> None:
        self._get_screen_locker().close()

    def _get_screen_locker(self) -> ScreenLocker:
        return self._features.get(FeatureName.SCREEN_LOCKER, ScreenLocker)


__all__ = ["CommandApi", "CommandDefinition"]
