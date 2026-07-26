# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportAttributeAccessIssue=false
"""Adapter truy vấn desktop Linux/Xorg.

File path: `src/agent/platform/linux/windows.py`.
Input: không nhận tham số; đọc desktop qua PyWinCtl rồi fallback `xdotool`.
Output: title/process active hoặc mapping các cửa sổ visible.
Nguyên lý: giữ fallback Xorg trong adapter; feature chỉ nhận dữ liệu chuẩn hóa.
"""

import shutil
import subprocess

import pywinctl as pwc


class LinuxWindowOperations:
    """Đọc desktop Linux, ưu tiên PyWinCtl và fallback xdotool."""

    def _run_xdotool(self, *arguments: str) -> str:
        executable = shutil.which("xdotool")
        if executable is None:
            return ""
        try:
            result = subprocess.run(
                [executable, *arguments],
                capture_output=True,
                check=False,
                text=True,
            )
        except OSError:
            return ""
        return result.stdout.strip() if result.returncode == 0 else ""

    def _active_with_xdotool(self) -> tuple[str, str]:
        window_id = self._run_xdotool("getactivewindow")
        if not window_id:
            return "", ""
        return (
            self._run_xdotool("getwindowname", window_id),
            self._run_xdotool("getwindowclassname", window_id),
        )

    def get_active_window(self) -> tuple[str, str]:
        """Trả cửa sổ active qua PyWinCtl hoặc fallback xdotool."""

        window = pwc.getActiveWindow()
        if window:
            active = window.title, window.getAppName()
            if any(active):
                return active
        return self._active_with_xdotool()

    def get_open_windows(self) -> dict[str, str]:
        """Trả cửa sổ visible qua PyWinCtl hoặc fallback xdotool."""

        windows = {
            window.title: window.getAppName()
            for window in pwc.getAllWindows()
        }
        if any(title or process for title, process in windows.items()):
            return windows
        return self._all_with_xdotool()

    def _all_with_xdotool(self) -> dict[str, str]:
        window_ids = self._run_xdotool("search", "--onlyvisible", "--name", ".")
        windows: dict[str, str] = {}
        for window_id in window_ids.splitlines():
            title = self._run_xdotool("getwindowname", window_id)
            process_name = self._run_xdotool("getwindowclassname", window_id)
            if title or process_name:
                windows[title] = process_name
        return windows
