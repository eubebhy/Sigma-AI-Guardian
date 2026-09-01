from uuid import UUID
from enum import Enum, auto


class Command(Enum):
    LOCK_SCREEN = auto()
    UNLOCK_SCREEN = auto()


class Request:
    id: UUID
    command: Command
