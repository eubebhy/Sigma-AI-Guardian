"""Đọc thông tin cửa sổ đang mở trên desktop.

File path: `src/system_monitor/windows_tracker/__init__.py`
Input: không nhận tham số; đọc state cửa sổ hiện tại qua `pywinctl`.
Output: tiêu đề cửa sổ active hoặc danh sách tiêu đề cửa sổ đang mở.

Nguyên lý hoạt động: module này bọc `pywinctl` để code giám sát không gọi trực
tiếp thư viện ngoài. Trên Linux, nếu `pywinctl` không trả về dữ liệu và hệ thống
có `xdotool`, module dùng `xdotool` để đọc tiêu đề và tên lớp của cửa sổ.
"""

import shutil
import subprocess as subp
import sys

import pywinctl as pwc


def _run_xdotool(*arguments: str) -> str:
    """Chạy một lệnh xdotool trên Linux và trả về stdout đã loại khoảng trắng."""

    if not sys.platform.startswith("linux"):
        return ""

    executable = shutil.which("xdotool")
    if executable is None:
        return ""

    try:
        result = subp.run(
            [executable, *arguments],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return ""

    return result.stdout.strip() if result.returncode == 0 else ""


def _get_active_window_with_xdotool() -> tuple[str, str]:
    """Đọc tiêu đề và tên lớp của cửa sổ active bằng xdotool."""

    window_id = _run_xdotool("getactivewindow")
    if not window_id:
        return "", ""

    title = _run_xdotool("getwindowname", window_id)
    process_name = _run_xdotool("getwindowclassname", window_id)
    return title, process_name


def _get_all_windows_with_xdotool() -> dict[str, str]:
    """Đọc các cửa sổ visible và tên lớp tương ứng bằng xdotool."""

    window_ids = _run_xdotool("search", "--onlyvisible", "--name", ".")
    windows: dict[str, str] = {}

    for window_id in window_ids.splitlines():
        title = _run_xdotool("getwindowname", window_id)
        process_name = _run_xdotool("getwindowclassname", window_id)
        if title or process_name:
            windows[title] = process_name

    return windows


def get_active_window_name() -> tuple[str, str]:
    """Trả về tiêu đề cửa sổ đang active, hoặc chuỗi rỗng nếu không có."""

    win = pwc.getActiveWindow()
    if win:
        active_window = win.title, win.getAppName()
        if any(active_window):
            return active_window

    return _get_active_window_with_xdotool()


def get_all_opening_windows() -> dict[str, str]:
    """Return all opening window with thier process name"""

    windows = pwc.getAllWindows()
    process_names: list[str] = []
    window_titles: list[str] = []

    for window in windows:
        window_titles.append(window.title)
        process_names.append(window.getAppName())

    opening_windows = dict(zip(window_titles, process_names))
    if any(title or process_name for title, process_name in opening_windows.items()):
        return opening_windows

    return _get_all_windows_with_xdotool()
