"""Adapter process Windows của SAG Agent.

File path: `src/agent/platform/windows/processes.py`.
Input: không nhận state; gọi `tasklist` hoặc PID cần kết thúc.
Output: process chuẩn hóa `(pid, name_lowercase)` hoặc thao tác kill.
Nguyên lý: giữ toàn bộ lệnh process Windows ở đây thay vì lặp trong feature.
"""

import csv
import subprocess

WINDOWS_PROTECTED_PROCESSES = [
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "logonui.exe",
    "lsass.exe",
    "services.exe",
    "winlogon.exe",
    "svchost.exe",
    # Windows desktop / basic session
    "explorer.exe",
    "dwm.exe",
    "sihost.exe",
    "taskhostw.exe",
    "ctfmon.exe",
    "fontdrvhost.exe",
    "RuntimeBroker.exe",
    "audiodg.exe",
    "conhost.exe",
    # Security / basic OS functionality
    "smartscreen.exe",
    "SecurityHealthService.exe",
    "SearchIndexer.exe",
]


class WindowsProcessOperations:
    """Thao tác process qua tasklist và taskkill."""

    def list_processes(self) -> list[tuple[int, str]]:
        """Đọc PID/name process từ `tasklist`; lỗi command được giữ nguyên cho caller."""

        output = subprocess.check_output(
            ["tasklist", "/fo", "csv", "/nh"],
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        processes: list[tuple[int, str]] = []
        for row in csv.reader(output.splitlines()):
            if len(row) >= 2 and row[1].strip().isdigit():
                processes.append((int(row[1]), row[0].strip().lower()))
        return processes

    def kill_process(self, pid: int) -> None:
        """Yêu cầu Windows kết thúc PID; exit code khác 0 được giữ nguyên cho caller."""

        subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True)

    def list_system_processes(self) -> list[str]:
        return WINDOWS_PROTECTED_PROCESSES
