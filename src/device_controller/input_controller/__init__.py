"""Public resource gửi input độc lập hệ điều hành.

File path: `src/device_controller/input_controller/__init__.py`.
Input: backend factory tùy chọn theo contract `InputControllerFactory`.
Output: `Input` cung cấp API keyboard/mouse và lifecycle `close()`.
Nguyên lý: mỗi object tạo một backend riêng; khi không truyền factory, object lấy
factory từ default platform services. `close()` đóng backend và xóa reference.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import wraps
from logging import getLogger
from typing import Callable, Concatenate, ParamSpec, TypeVar

from agent.platform_protocols import (
    InputControllerOperations,
    MouseButton,
)

logger = getLogger(__name__)

_P = ParamSpec("_P")
_R = TypeVar("_R")


class LinuxInputWereRecreatedBeforeClose(Exception):
    pass


# Xử lý lỗi chung cho các method gửi input qua backend.
def handle_error(
    # Callable nhan vao:
    # Concatenate[Input, _P] - chinh la self va cac tham so khac
    # Dau ra la _R - chinh la dau ra cua ham ban dau
    #
    # Tom lai ty[e hien nay la nhan vao cai gi, tra ve cai do y chang
    func: Callable[Concatenate[Input, _P], _R],
) -> Callable[Concatenate[Input, _P], _R]:
    """Chiu trach nhieu su ly neu co loi khi goi cac method cua Input
    Khi co loi no se:
        1. Log lai, warning
        2. Thu tao lai backend
        3. Goi lai method
        4. Neu goi lai method lai loi -> Raise"""

    @wraps(func)
    def logger_if_error(self: Input, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        try:
            return func(self, *args, **kwargs)
        except LinuxInputWereRecreatedBeforeClose:
            raise  # Raise ma khong truyen gi thi giu nguyen exception goc

        except Exception as error:
            logger.warning(
                "Error while sending input: %s. Recreating backend and retrying.",
                error,
            )
            self.close()
            self.create()
            return func(self, *args, **kwargs)

    return logger_if_error


class Input:
    """Resource sở hữu một input backend độc lập."""

    def __init__(self, backend: InputControllerOperations | None = None) -> None:
        if backend is None:
            from agent.platform import get_default_platform_services

            backend = get_default_platform_services().input_controller
        self._backend: InputControllerOperations = backend

    def _operations(self) -> InputControllerOperations:
        return self._backend

    # Cac ham dieu khien
    # NOTE: Khong can luu trang thai close hay chua vi backend da su ly

    @handle_error
    def click(
        self,
        x: int | None = None,
        y: int | None = None,
        button: MouseButton = "primary",
    ) -> None:
        self._operations().click(x, y, button)

    @handle_error
    def keyDown(self, key: str) -> None:
        self._operations().keyDown(key)

    @handle_error
    def keyUp(self, key: str) -> None:
        self._operations().keyUp(key)

    @handle_error
    def mouseDown(self, button: MouseButton) -> None:
        self._operations().mouseDown(button)

    @handle_error
    def mouseUp(self, button: MouseButton) -> None:
        self._operations().mouseUp(button)

    @handle_error
    def moveRel(self, x: int | None, y: int | None, duration: float = 0.0) -> None:
        self._operations().moveRel(x, y, duration)

    @handle_error
    def moveTo(self, x: int | None, y: int | None, duration: float = 0.0) -> None:
        self._operations().moveTo(x, y, duration)

    @handle_error
    def position(self, take_new: bool = False) -> tuple[int, int]:
        return self._operations().position(take_new)

    @handle_error
    def press(self, keys: str | Sequence[str]) -> None:
        self._operations().press(keys)

    @handle_error
    def scroll(self, amount: int) -> None:
        self._operations().scroll(amount)

    @handle_error
    def sideScroll(self, amount: int) -> None:
        self._operations().sideScroll(amount)

    @handle_error
    def supportedKeys(self) -> tuple[str, ...]:
        return self._operations().supportedKeys()

    @handle_error
    def supportedWriteCharacters(self) -> str:
        return self._operations().supportedWriteCharacters()

    @handle_error
    def write(self, message: str, interval: float = 0.0) -> None:
        self._operations().write(message, interval)

    def close(self) -> None:
        """Đóng backend; giữ reference nếu cleanup lỗi để caller có thể retry."""
        self._backend.close()

    def create(self):
        # Canh bao rui ro quan ly lifecycle sai
        if not self._backend._closed:
            raise RuntimeError("Linux Input were recreated before close()")

        self._backend.create()


__all__ = ["Input"]
