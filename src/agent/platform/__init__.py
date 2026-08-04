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
from dataclasses import dataclass
from collections.abc import Iterator, Sequence
from typing import NoReturn

import logging
from agent.capabilities import PlatformCapabilities
from agent.contracts import (
    BrowserOperations,
    HostsPathOperations,
    InputBlockingOperations,
    InputControllerOperations,
    KeyListenerOperations,
    ProcessOperations,
    WindowOperations,
    CursorOperations,
)


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
    input_blocker: InputBlockingOperations
    key_listener: KeyListenerOperations
    input_controller: InputControllerOperations
    cursor_controller: CursorOperations


logger = logging.getLogger(__name__)


def create_platform_services(platform_name: str | None = None) -> PlatformServices:
    """Tao adpter theo moi truong."""

    normalized_name = platform_name or platform.system().lower()
    logger.debug("Detected platform: %s", normalized_name)

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
