# pyright: reportPrivateUsage=false
"""Contract test cho feature SAG Agent không cần desktop hay process thật."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from device_controler.process_killer import ProcessKiller
from device_controler import browser_tab
from system_monitor.windows_tracker import get_all_opening_windows
from agent.capabilities import PlatformCapabilities
from agent.platform import PlatformServices


class _FakeProcessOperations:
    def __init__(self) -> None:
        self.killed_processes: list[int] = []

    def list_processes(self) -> list[tuple[int, str]]:
        return [(101, "game.exe"), (102, "teacher-tool.exe")]

    def kill_process(self, pid: int) -> None:
        self.killed_processes.append(pid)


class _FakeWindowOperations:
    def get_active_window(self) -> tuple[str, str]:
        return "Lesson", "teacher-tool.exe"

    def get_open_windows(self) -> dict[str, str]:
        return {"Lesson": "teacher-tool.exe"}


class _FakeBrowserOperations:
    def __init__(self) -> None:
        self.default_urls: list[str] = []
        self.executable_lookups: list[tuple[str, ...]] = []

    def launch(self, command: list[str]) -> bool:
        del command
        return False

    def open_default_url(self, url: str) -> bool:
        self.default_urls.append(url)
        return True

    def find_executable(self, executables: tuple[str, ...]) -> str | None:
        self.executable_lookups.append(executables)
        return None


class _FakeHostsPathOperations:
    def get_hosts_path(self) -> Path:
        return Path("/tmp/hosts")


class AgentPlatformTests(unittest.TestCase):
    """Feature phải dùng contract thay vì gọi API desktop/native trực tiếp."""

    def test_process_killer_uses_injected_process_operations(self) -> None:
        operations = _FakeProcessOperations()
        killer = ProcessKiller(process_operations=operations)
        killer.set_blacklist(["game.exe"])

        killer._scan_and_kill()

        self.assertEqual(operations.killed_processes, [101])

    def test_window_tracker_uses_injected_window_operations(self) -> None:
        windows = get_all_opening_windows(_FakeWindowOperations())

        self.assertEqual(windows, {"Lesson": "teacher-tool.exe"})

    def test_browser_fallback_uses_injected_platform_adapter(self) -> None:
        browser_operations = _FakeBrowserOperations()
        services = PlatformServices(
            name="Test",
            capabilities=PlatformCapabilities(platform_name="Test", items=()),
            processes=_FakeProcessOperations(),
            browser=browser_operations,
            windows=_FakeWindowOperations(),
            hosts=_FakeHostsPathOperations(),
        )

        with patch.object(
            browser_tab,
            "get_default_platform_services",
            side_effect=AssertionError("explicit services must not create defaults"),
        ):
            self.assertTrue(browser_tab.open_tab("https://example.com", services))
        self.assertEqual(browser_operations.default_urls, ["https://example.com"])

    def test_browser_discovery_uses_injected_platform_adapter(self) -> None:
        browser_operations = _FakeBrowserOperations()

        browser_tab._browser_states(_FakeProcessOperations(), browser_operations)

        self.assertEqual(len(browser_operations.executable_lookups), len(browser_tab.BROWSERS))


if __name__ == "__main__":
    unittest.main()
