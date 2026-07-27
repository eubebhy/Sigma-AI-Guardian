# pyright: reportPrivateUsage=false
"""Kiểm tra browser tab bằng adapter fake hoặc mock.

File path: ``tests/test_browser.py``. Input: safe suite dùng adapter fake/mock;
manual command nhận URL HTTP hoặc HTTPS. Output: in kết quả ``opened`` hoặc
thông báo lỗi. Nguyên lý: chỉ ``real open`` gọi browser adapter của platform và bắt
exception của ``open_tab()``.

Lệnh manual chính xác: ``./.pyvenv/bin/python tests/test_browser.py real open
https://example.com``. Preflight/prerequisites: có desktop session và browser mặc
định hoặc browser được hỗ trợ trong PATH. Side effect: mở URL trong browser thật,
có thể tạo process/tab. Ctrl+C trước khi browser nhận lệnh dừng runner; sau khi lệnh
đã mở tab thì Ctrl+C không đóng tab đó.
"""

from __future__ import annotations

import argparse
from io import StringIO
from pathlib import Path
import sys
import unittest
from collections.abc import Sequence
from typing import NoReturn
from unittest.mock import patch

from test_support import add_source_path, run_module, test_modes


add_source_path()

from agent.capabilities import PlatformCapabilities
from agent.platform import PlatformServices
from device_controler import browser_tab


class _RealArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _parse_real_arguments(arguments: Sequence[str]) -> argparse.Namespace | None:
    parser = _RealArgumentParser(add_help=False)
    commands = parser.add_subparsers(dest="command", required=True)
    open_command = commands.add_parser("open", add_help=False)
    open_command.add_argument("url")
    try:
        command = parser.parse_args(arguments)
    except (argparse.ArgumentError, ValueError):
        return None
    if not command.url.startswith(("http://", "https://")):
        return None
    return command


def run_real(arguments: Sequence[str]) -> int:
    """Mở URL có chủ đích, không được gọi bởi safe suite."""

    command = _parse_real_arguments(arguments)
    if command is None:
        print("Usage: real open URL", file=sys.stderr)
        return 2
    try:
        browser_tab.open_tab(command.url)
    except KeyboardInterrupt:
        print("Open interrupted")
        return 130
    except Exception as error:
        print(f"Open failed: {error}", file=sys.stderr)
        return 1
    print("opened")
    return 0


class _FakeProcessOperations:
    def list_processes(self) -> list[tuple[int, str]]:
        return []

    def kill_process(self, pid: int) -> None:
        del pid


class _FakeWindowOperations:
    def get_active_window(self) -> tuple[str, str]:
        return "", ""

    def get_open_windows(self) -> dict[str, str]:
        return {}


class _FakeHostsPathOperations:
    def get_hosts_path(self) -> Path:
        return Path("/tmp/hosts")


class _FakeBrowserOperations:
    def __init__(self, default_open_result: bool = True) -> None:
        self.default_urls: list[str] = []
        self.executable_lookups: list[tuple[str, ...]] = []
        self.default_open_result = default_open_result

    def launch(self, command: list[str]) -> bool:
        del command
        return False

    def open_default_url(self, url: str) -> bool:
        self.default_urls.append(url)
        return self.default_open_result

    def find_executable(self, executables: tuple[str, ...]) -> str | None:
        self.executable_lookups.append(executables)
        return None


class BrowserTests(unittest.TestCase):
    @test_modes("fake")
    def test_open_tab_rejects_invalid_url(self) -> None:
        with self.assertRaisesRegex(ValueError, "HTTP or HTTPS"):
            browser_tab.open_tab("file:///tmp/a.html")

    @test_modes("fake")
    def test_open_tab_raises_when_all_launches_fail(self) -> None:
        browser_operations = _FakeBrowserOperations(default_open_result=False)
        services = PlatformServices(
            name="Test",
            capabilities=PlatformCapabilities(platform_name="Test", items=()),
            processes=_FakeProcessOperations(),
            browser=browser_operations,
            windows=_FakeWindowOperations(),
            hosts=_FakeHostsPathOperations(),
        )
        browser = {
            "spec": browser_tab.BROWSERS[0],
            "executable": "/bin/browser",
            "pid": None,
            "score": 10,
        }

        with patch.object(browser_tab, "_pick_browser", side_effect=([], [browser])):
            with self.assertRaisesRegex(RuntimeError, "https://example.com"):
                browser_tab.open_tab("https://example.com", services)

        self.assertEqual(browser_operations.default_urls, ["https://example.com"])

    @test_modes("mock", "smoke")
    def test_open_tab_uses_running_browser(self) -> None:
        browser = {
            "spec": browser_tab.BROWSERS[0],
            "executable": "/bin/browser",
            "pid": 123,
            "score": 1000,
        }
        with (
            patch.object(browser_tab, "_pick_browser", return_value=[browser]),
            patch.object(browser_tab, "_run_open_command", return_value=True) as open_command,
        ):
            self.assertTrue(browser_tab.open_tab("https://example.com"))

        open_command.assert_called_once_with(["/bin/browser", "https://example.com"])

    @test_modes("fake")
    def test_fallback_uses_injected_platform_adapter(self) -> None:
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

    @test_modes("fake")
    def test_discovery_uses_injected_platform_adapter(self) -> None:
        browser_operations = _FakeBrowserOperations()

        browser_tab._browser_states(_FakeProcessOperations(), browser_operations)

        self.assertEqual(len(browser_operations.executable_lookups), len(browser_tab.BROWSERS))

    @test_modes("real")
    def test_open_tab_uses_current_platform_browser(self) -> None:
        self.assertTrue(browser_tab.open_tab("https://example.com"))


class RealBrowserCommandTests(unittest.TestCase):
    def test_parse_real_open_command(self) -> None:
        command = _parse_real_arguments(("open", "https://example.com"))

        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.command, "open")
        self.assertEqual(command.url, "https://example.com")

    def test_parse_real_open_rejects_non_http_url(self) -> None:
        self.assertIsNone(_parse_real_arguments(("open", "file:///tmp/a.html")))

    def test_run_real_reports_browser_error(self) -> None:
        with (
            patch.object(
                browser_tab,
                "open_tab",
                side_effect=RuntimeError("No browser could open the URL"),
            ),
            patch("sys.stderr", new_callable=StringIO) as standard_error,
        ):
            result = run_real(("open", "https://example.com"))

        self.assertEqual(result, 1)
        self.assertIn("Open failed: No browser could open the URL", standard_error.getvalue())


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
