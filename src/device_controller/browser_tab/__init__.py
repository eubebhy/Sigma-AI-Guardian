"""Mo tab browser theo browser dang co tren may.

File path: `src/device_controller/browser_tab/__init__.py`
Input contract:
- open_tab(url): nhan url bat dau bang http:// hoac https://.
Output contract:
- Tra ve True neu goi duoc browser hop le.
- Raise ValueError neu url khong bat dau bang http:// hoac https://.
- Raise RuntimeError neu tat ca lan mo browser deu that bai.
Operating principle:
- Lay process browser dang chay va executable co trong PATH.
- Uu tien browser dang chay, roi fallback sang browser co executable.
- Cuoi cung dung default browser cua OS.
"""

from __future__ import annotations

from typing import TypedDict

from agent.platform_protocols import BrowserOperations, ProcessOperations
from agent.platform import PlatformServices, get_default_platform_services


class BrowserSpec(TypedDict):
    name: str
    executables: tuple[str, ...]
    processes: tuple[str, ...]


class BrowserState(TypedDict):
    spec: BrowserSpec
    executable: str | None
    pid: int | None
    score: int


BROWSER_SPECS: tuple[BrowserSpec, ...] = (
    {
        "name": "chrome",
        "executables": ("google-chrome", "chrome", "chrome.exe"),
        "processes": ("chrome", "chrome.exe", "google-chrome"),
    },
    {
        "name": "edge",
        "executables": ("msedge", "msedge.exe"),
        "processes": ("msedge", "msedge.exe"),
    },
    {
        "name": "firefox",
        "executables": ("firefox", "firefox.exe"),
        "processes": ("firefox", "firefox.exe"),
    },
    {
        "name": "brave",
        "executables": ("brave-browser", "brave", "brave.exe"),
        "processes": ("brave", "brave.exe", "brave-browser"),
    },
    {
        "name": "opera",
        "executables": ("opera", "opera.exe"),
        "processes": ("opera", "opera.exe"),
    },
    {
        "name": "chromium",
        "executables": ("chromium", "chromium-browser", "chromium.exe"),
        "processes": ("chromium", "chromium-browser", "chromium.exe"),
    },
    {
        "name": "vivaldi",
        "executables": ("vivaldi", "vivaldi.exe"),
        "processes": ("vivaldi", "vivaldi.exe"),
    },
    {
        "name": "coccoc",
        "executables": ("coccoc", "coccoc.exe"),
        "processes": ("coccoc", "coccoc.exe"),
    },
    {
        "name": "tor",  # Mac du that te chang ai dung TOR Browser tren truong
        "executables": ("tor-browser", "tor.exe"),
        "processes": ("tor", "tor-browser", "tor.exe"),
    },
    {
        "name": "yandex",
        "executables": ("yandex-browser", "yandex.exe"),
        "processes": ("yandex-browser", "yandex.exe"),
    },
    {
        "name": "waterfox",
        "executables": ("waterfox", "waterfox.exe"),
        "processes": ("waterfox", "waterfox.exe"),
    },
)


def _find_pid(spec: BrowserSpec, processes: dict[str, int]) -> int | None:
    for process_name in spec["processes"]:
        if process_name.lower() in processes:
            return processes[process_name.lower()]
    return None


def _score_browser(pid: int | None, index: int) -> int:
    score = 10 - index
    if pid is not None:
        score += 1000
    return score


def _browser_states(
    process_operations: ProcessOperations | None = None,
    browser_operations: BrowserOperations | None = None,
) -> list[BrowserState]:
    if process_operations is None or browser_operations is None:
        default_services = get_default_platform_services()
        if process_operations is None:
            process_operations = default_services.processes
        if browser_operations is None:
            browser_operations = default_services.browser
    processes = {name: pid for pid, name in process_operations.list_processes()}
    states: list[BrowserState] = []
    for index, spec in enumerate(BROWSER_SPECS):
        pid = _find_pid(spec, processes)
        executable = browser_operations.find_executable(spec["executables"])
        score = _score_browser(pid, index)
        states.append(
            {"spec": spec, "executable": executable, "pid": pid, "score": score}
        )
    return states


def _pick_browser(
    require_running: bool,
    process_operations: ProcessOperations | None = None,
    browser_operations: BrowserOperations | None = None,
) -> list[BrowserState]:
    states = _browser_states(process_operations, browser_operations)
    if require_running:
        states = [state for state in states if state["pid"] is not None]
    states = [state for state in states if state["executable"] is not None]
    states.sort(key=lambda state: state["score"], reverse=True)
    return states


def _run_open_command(
    command: list[str],
    browser_operations: BrowserOperations | None = None,
) -> bool:
    """Khởi chạy command qua adapter browser của platform hiện tại."""

    operations = browser_operations or get_default_platform_services().browser
    return operations.launch(command)


def open_tab(url: str, platform_services: PlatformServices | None = None) -> bool:
    """Mở URL bằng browser phù hợp nhất trên máy hiện tại.

    URL phải bắt đầu bằng `http://` hoặc `https://`. Hàm ưu tiên browser đang chạy
    để tab mới xuất hiện đúng phiên người dùng, sau đó mới fallback sang browser
    có executable trong PATH và cuối cùng là default browser của OS. Raise
    `ValueError` khi URL không hợp lệ và `RuntimeError` khi không mở được URL.
    """

    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid URL {url!r}: must start with HTTP or HTTPS")

    if platform_services is None:
        for browser in _pick_browser(require_running=True):
            if browser["executable"] and _run_open_command(
                [browser["executable"], url]
            ):
                return True
        for browser in _pick_browser(require_running=False):
            if browser["executable"] and _run_open_command(
                [browser["executable"], url]
            ):
                return True
        if get_default_platform_services().browser.open_default_url(url):
            return True
    else:
        for browser in _pick_browser(
            True,
            platform_services.processes,
            platform_services.browser,
        ):
            if browser["executable"] and _run_open_command(
                [browser["executable"], url], platform_services.browser
            ):
                return True
        for browser in _pick_browser(
            False,
            platform_services.processes,
            platform_services.browser,
        ):
            if browser["executable"] and _run_open_command(
                [browser["executable"], url], platform_services.browser
            ):
                return True
        if platform_services.browser.open_default_url(url):
            return True

    raise RuntimeError(f"Could not open URL after all browser launch attempts: {url}")


__all__ = ["open_tab"]
