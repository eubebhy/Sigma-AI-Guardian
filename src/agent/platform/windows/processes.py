"""Adapter process Windows của SAG Agent.

File path: `src/agent/platform/windows/processes.py`.
Input: không nhận state; gọi `tasklist` hoặc PID cần kết thúc.
Output: process chuẩn hóa `(pid, name_lowercase)` hoặc thao tác kill.
Nguyên lý: giữ toàn bộ lệnh process Windows ở đây thay vì lặp trong feature.
"""

import csv
import subprocess


class WindowsProcessOperations:
    """Thao tác process qua tasklist và taskkill."""

    def list_processes(self) -> list[tuple[int, str]]:
        """Đọc PID/name process từ `tasklist`; lỗi command trả danh sách rỗng."""

        try:
            output = subprocess.check_output(
                ["tasklist", "/fo", "csv", "/nh"],
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
        except (OSError, subprocess.SubprocessError):
            return []
        processes: list[tuple[int, str]] = []
        for row in csv.reader(output.splitlines()):
            if len(row) >= 2 and row[1].strip().isdigit():
                processes.append((int(row[1]), row[0].strip().lower()))
        return processes

    def kill_process(self, pid: int) -> None:
        """Yêu cầu Windows kết thúc PID như hành vi ProcessKiller cũ."""

        subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False)
