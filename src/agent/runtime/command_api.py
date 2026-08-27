"""Allowlist command nội bộ của SAG Agent Runtime.

File path: `src/agent/runtime/command_api.py`.
Input: `Request` đã decode bởi local transport tương lai.
Output: `Response` thành công hoặc lỗi chuẩn hóa.
Nguyên lý: action map trực tiếp tới handler đã định nghĩa, không dispatch object/method tùy ý.
"""

from collections.abc import Callable

from agent.runtime.feature_manager import FeatureManager
from agent.runtime.request_types import (
    Request,
    RequestFailed,
    RequestSuccessful,
    Response,
)


class CommandApi:
    """Route command được cho phép tới feature do Runtime sở hữu."""

    def __init__(
        self,
        features: FeatureManager,
        is_running: Callable[[], bool],
    ) -> None:
        self._features = features
        self._is_running = is_running
        self._handlers: dict[str, Callable[[Request], object]] = {
            "get_agent_status": self._get_agent_status,
            "lock_screen": self._lock_screen,
        }

    def execute(self, request: Request) -> Response:
        handler = self._handlers.get(request.action)
        if handler is None:
            return Response(
                request.id,
                RequestFailed("Unsupported command", "unsupported_command"),
            )
        try:
            return Response(request.id, RequestSuccessful(), handler(request))
        except Exception as error:
            return Response(request.id, RequestFailed(str(error), "command_failed"))

    def _get_agent_status(self, _request: Request) -> object:
        return {
            "state": "running" if self._is_running() else "stopped",
            "active_features": self._features.active_features(),
        }

    def _lock_screen(self, _request: Request) -> object:
        locker = self._features.get("screen_locker")
        lock = getattr(locker, "lock", None)
        if not callable(lock):
            raise TypeError("Feature screen_locker does not provide lock()")
        lock()
        return None


__all__ = ["CommandApi"]
