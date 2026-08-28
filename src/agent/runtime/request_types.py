"""Contract request và response của SAG Agent Runtime.

File path: `src/agent/runtime/request_types.py`.
Input: command đã được decode từ transport thành `Request`.
Output: `Response` biểu diễn trạng thái và kết quả của command.
Nguyên lý: command và feature dùng enum; Runtime không nhận identifier string tự do.
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class CommandName(StrEnum):
    """Các command công khai mà Agent Runtime hỗ trợ."""

    GET_AGENT_STATUS = "get_agent_status"
    LOCK_SCREEN = "lock_screen"
    UNLOCK_SCREEN = "unlock_screen"


class FeatureName(StrEnum):
    """Các feature do Agent Runtime quản lý."""

    PROCESS_GUARD = "process_guard"
    WEB_BLOCKER = "web_blocker"
    CLASSIFIER = "classifier"
    SCREEN_LOCKER = "screen_locker"
    BROWSER_TAB = "browser_tab"


@dataclass(frozen=True)
class Request:
    """Một command đã được validate trước khi Runtime thực thi."""

    id: UUID
    command: CommandName


class AgentState(StrEnum):
    """Trạng thái vận hành hiện tại của Agent Runtime."""

    RUNNING = "running"
    STOPPED = "stopped"


@dataclass(frozen=True)
class AgentStatus:
    """Dữ liệu trả về của command `GET_AGENT_STATUS`."""

    state: AgentState
    active_features: tuple[FeatureName, ...]


class RequestStatus(StrEnum):
    """Trạng thái lifecycle của command theo `Request.id`."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    INVALID = "invalid"
    EXPIRED = "expired"


@dataclass(frozen=True)
class Response:
    """Trạng thái hoặc kết quả hiện tại của một command."""

    id: UUID
    status: RequestStatus
    data: AgentStatus | None = None
    reason: str | None = None
    error_code: str | None = None


__all__ = [
    "CommandName",
    "AgentState",
    "AgentStatus",
    "FeatureName",
    "Request",
    "RequestStatus",
    "Response",
]
