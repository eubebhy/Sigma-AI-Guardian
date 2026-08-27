from dataclasses import dataclass
from typing import Any
from uuid import UUID


# =========================
# Request
# =========================


@dataclass(frozen=True)
class Request:
    id: UUID
    action: str
    payload: Any = None


# =========================
# Response
# =========================


@dataclass(frozen=True)
class Response:
    request_id: UUID
    status: "RequestStatus"
    data: Any = None


# =========================
# Status
# =========================


class RequestStatus:
    pass


@dataclass(frozen=True)
class RequestSuccessful(RequestStatus):
    """Request đã được thực hiện thành công."""


@dataclass(frozen=True)
class RequestFailed(RequestStatus):
    reason: str
    error_code: str | None = None


class RequestExpired(RequestStatus):
    pass


class RequestRejected(RequestStatus):
    """Request hop le nhung agent tu choi thuc thi."""

    pass


class RequestInvalid(RequestStatus):
    """Request ko hop le."""

    pass
