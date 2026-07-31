"""Adapter Windows của SAG Agent.

File path: `src/agent/platform/windows/__init__.py`.
Input: factory runtime gọi `create_services()`.
Output: adapter Windows chuẩn hóa theo contract Agent.
Nguyên lý: module ghép adapter capability nhỏ; feature không import package này.
"""

from agent.capabilities import Capability, PlatformCapabilities
from agent.platform import PlatformServices
from agent.platform.windows.browser import WindowsBrowserOperations
from agent.platform.windows.hide_cursor import WindowsCursorOperation
from agent.platform.windows.hosts import WindowsHostsPathOperations
from agent.platform.windows.input_blocker import WindowsInputBlockingOperations
from agent.platform.windows.input_controller_operations import (
    WindowsInputControllerOperations,
)
from agent.platform.windows.key_listener import WindowsKeyListenerOperations
from agent.platform.windows.processes import WindowsProcessOperations
from agent.platform.windows.windows import WindowsWindowOperations


def create_services() -> PlatformServices:
    """Tạo tập adapter Windows cho runtime hiện tại."""

    capabilities = PlatformCapabilities(
        platform_name="Windows",
        items=(
            Capability("process_control", True, "tasklist and taskkill"),
            Capability("browser_launch", True, "Windows subprocess"),
            Capability("window_tracking", True, "PyWinCtl"),
            Capability("hosts_file", True, "Administrator permission required"),
            Capability("input_blocking", True, "Administrator permission required"),
            Capability("input_listening", True, "pynput and Win32"),
            Capability("input_control", True, "pydirectinput and Win32"),
            Capability("cursor_controller", True, "X11 backend, cursor blur control"),
        ),
    )
    return PlatformServices(
        name="Windows",
        capabilities=capabilities,
        processes=WindowsProcessOperations(),
        browser=WindowsBrowserOperations(),
        windows=WindowsWindowOperations(),
        hosts=WindowsHostsPathOperations(),
        input_blocker=WindowsInputBlockingOperations(),
        key_listener=WindowsKeyListenerOperations(),
        input_controller=WindowsInputControllerOperations(),
        cursor_controller=WindowsCursorOperation(),
    )
