"""Adapter Windows của SAG Agent.

File path: `src/agent/platform/windows/__init__.py`.
Input: factory runtime gọi `create_services()`.
Output: adapter Windows chuẩn hóa theo contract Agent.
Nguyên lý: module ghép adapter capability nhỏ; feature không import package này.
"""

from agent.platform import PlatformServices
from agent.platform.windows.browser import WindowsBrowserOperations
from agent.platform.windows.cursor import WindowsCursorOperations
from agent.platform.windows.hosts import WindowsHostsPathOperations
from agent.platform.windows.input_blocker import WindowsInputBlockingOperations
from agent.platform.windows.input_controller import WindowsInput
from agent.platform.windows.key_listener import WindowsKeyListenerOperations
from agent.platform.windows.processes import WindowsProcessOperations
from agent.platform.windows.windows import WindowsWindowOperations


def create_services() -> PlatformServices:
    """Tạo tập adapter Windows cho runtime hiện tại."""

    return PlatformServices(
        name="Windows",
        processes=WindowsProcessOperations(),
        browser=WindowsBrowserOperations(),
        windows=WindowsWindowOperations(),
        hosts=WindowsHostsPathOperations(),
        input_blocker=WindowsInputBlockingOperations(),
        key_listener=WindowsKeyListenerOperations(),
        input_controller=WindowsInput(),
        cursor_controller=WindowsCursorOperations(),
    )
