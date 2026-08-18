"""Adapter Linux của SAG Agent.

File path: `src/agent/platform/linux/__init__.py`.
Input: factory runtime gọi `create_services()`.
Output: adapter Linux chuẩn hóa theo contract Agent.
Nguyên lý: module ghép adapter capability nhỏ; feature không import package này.
"""

from agent.platform import PlatformServices
from agent.platform.linux.browser import LinuxBrowserOperations
from agent.platform.linux.hosts import LinuxHostsPathOperations
from agent.platform.linux.input_blocker import LinuxInputBlockingOperations
from agent.platform.linux.input_controller import LinuxInput
from agent.platform.linux.key_listener import LinuxKeyListenerOperations
from agent.platform.linux.processes import LinuxProcessOperations
from agent.platform.linux.windows import LinuxWindowOperations
from agent.platform.linux.cursor import LinuxCursorOperations


def create_services() -> PlatformServices:
    """Tạo tập adapter Linux cho runtime hiện tại."""

    return PlatformServices(
        name="Linux",
        processes=LinuxProcessOperations(),
        browser=LinuxBrowserOperations(),
        windows=LinuxWindowOperations(),
        hosts=LinuxHostsPathOperations(),
        input_blocker=LinuxInputBlockingOperations(),
        key_listener=LinuxKeyListenerOperations(),
        input_controller=LinuxInput(),
        cursor_controller=LinuxCursorOperations(),
    )
