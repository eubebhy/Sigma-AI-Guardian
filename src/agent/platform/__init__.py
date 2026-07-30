"""Chọn adapter Windows hoặc Linux cho một SAG Agent runtime.

File path: `src/agent/platform/__init__.py`.
Input: `platform_name` tùy chọn từ runtime hoặc test.
Output: `PlatformServices` có capability và adapter process, browser, window, hosts,
input blocker, key listener, input controller.
Nguyên lý: chuẩn hóa tên OS rồi lazy import đúng package platform; OS khác fail rõ.
"""

from __future__ import annotations

import platform
import threading
from dataclasses import dataclass, field
from collections.abc import Iterator, Sequence
from typing import NoReturn

from agent.capabilities import PlatformCapabilities
from agent.contracts import (
    BrowserOperations,
    HostsPathOperations,
    InputBlockingOperations,
    InputControllerOperations,
    KeyListenerOperations,
    KeyEvent,
    MouseButton,
    MouseEvent,
    ProcessOperations,
    WindowOperations,
)


def _raise_missing_input_operations() -> NoReturn:
    raise NotImplementedError("Input operations were not configured")


class _MissingInputBlockingOperations:
    def block(self) -> None:
        _raise_missing_input_operations()

    def unblock(self) -> None:
        _raise_missing_input_operations()

    def close(self) -> None:
        return None


class _MissingKeyListenerOperations:
    def get_num_lock_state(self) -> bool:
        _raise_missing_input_operations()

    def listen_keys(
        self,
        timeout: float | None = None,
        stop_event: threading.Event | None = None,
    ) -> Iterator[KeyEvent]:
        del timeout, stop_event
        _raise_missing_input_operations()

    def listen_mice(
        self,
        timeout: float | None = None,
        stop_event: threading.Event | None = None,
    ) -> Iterator[MouseEvent]:
        del timeout, stop_event
        _raise_missing_input_operations()

    def close(self) -> None:
        return None


class _MissingInputControllerOperations:
    def click(self, x: int | None = None, y: int | None = None,
              button: MouseButton = "primary") -> None:
        del x, y, button
        _raise_missing_input_operations()

    def keyDown(self, key: str) -> None:
        del key
        _raise_missing_input_operations()

    def keyUp(self, key: str) -> None:
        del key
        _raise_missing_input_operations()

    def mouseDown(self, button: MouseButton) -> None:
        del button
        _raise_missing_input_operations()

    def mouseUp(self, button: MouseButton) -> None:
        del button
        _raise_missing_input_operations()

    def moveRel(self, x: int | None, y: int | None,
                duration: float = 0.0) -> None:
        del x, y, duration
        _raise_missing_input_operations()

    def moveTo(self, x: int | None, y: int | None,
               duration: float = 0.0) -> None:
        del x, y, duration
        _raise_missing_input_operations()

    def position(self, take_new: bool = False) -> tuple[int, int]:
        del take_new
        _raise_missing_input_operations()

    def press(self, keys: str | Sequence[str]) -> None:
        del keys
        _raise_missing_input_operations()

    def scroll(self, amount: int) -> None:
        del amount
        _raise_missing_input_operations()

    def sideScroll(self, amount: int) -> None:
        del amount
        _raise_missing_input_operations()

    def supportedKeys(self) -> tuple[str, ...]:
        _raise_missing_input_operations()

    def supportedWriteCharacters(self) -> str:
        _raise_missing_input_operations()

    def write(self, message: str, interval: float = 0.0) -> None:
        del message, interval
        _raise_missing_input_operations()

    def close(self) -> None:
        return None


# Doi tuong bat bien, khong the thay doi gia tri truyen vao sau khi tao
# PlatformServices()
@dataclass(frozen=True)
class PlatformServices:
    """Các adapter OS được tạo một lần cho một Agent runtime."""

    name: str
    capabilities: PlatformCapabilities
    processes: ProcessOperations
    browser: BrowserOperations
    windows: WindowOperations
    hosts: HostsPathOperations
    input_blocker: InputBlockingOperations = field(
        default_factory=_MissingInputBlockingOperations
    )
    key_listener: KeyListenerOperations = field(
        default_factory=_MissingKeyListenerOperations
    )
    input_controller: InputControllerOperations = field(
        default_factory=_MissingInputControllerOperations
    )


def create_platform_services(platform_name: str | None = None) -> PlatformServices:
    """Tao adpter theo moi truong."""

    normalized_name = platform_name or platform.system().lower()

    if normalized_name in {"linux"}:
        from agent.platform.linux import create_services

        return create_services()
    if normalized_name in {"windows", "win32"}:
        from agent.platform.windows import create_services

        return create_services()
    raise NotImplementedError(f"Unsupported platform: {normalized_name}")


_default_services: PlatformServices | None = None
_default_services_lock = threading.Lock()


def get_default_platform_services() -> PlatformServices:
    """Trả adapter process-wide cho caller compatibility không có runtime."""

    global _default_services

    with _default_services_lock:
        if _default_services is None:
            _default_services = create_platform_services()
    return _default_services


__all__ = [
    "PlatformServices",
    "create_platform_services",
    "get_default_platform_services",
]
