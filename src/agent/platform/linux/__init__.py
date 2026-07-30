"""Adapter Linux của SAG Agent.

File path: `src/agent/platform/linux/__init__.py`.
Input: factory runtime gọi `create_services()`.
Output: adapter Linux chuẩn hóa theo contract Agent.
Nguyên lý: module ghép adapter capability nhỏ; feature không import package này.
"""

from agent.capabilities import Capability, PlatformCapabilities
from agent.platform import PlatformServices
from agent.platform.linux.browser import LinuxBrowserOperations
from agent.platform.linux.hosts import LinuxHostsPathOperations
from agent.platform.linux.processes import LinuxProcessOperations
from agent.platform.linux.windows import LinuxWindowOperations


def create_services() -> PlatformServices:
    """Tạo tập adapter Linux cho runtime hiện tại."""

    capabilities = PlatformCapabilities(
        platform_name="Linux",
        items=(
            Capability("process_control", True, "ps and SIGKILL"),
            Capability("browser_launch", True, "subprocess"),
            Capability("window_tracking", True, "PyWinCtl with xdotool fallback"),
            Capability("hosts_file", True, "/etc/hosts permission required"),
        ),
    )
    return PlatformServices(
        name="Linux",
        capabilities=capabilities,
        processes=LinuxProcessOperations(),
        browser=LinuxBrowserOperations(),
        windows=LinuxWindowOperations(),
        hosts=LinuxHostsPathOperations(),
    )
