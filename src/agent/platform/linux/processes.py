"""Adapter process Linux của SAG Agent.

File path: `src/agent/platform/linux/processes.py`.
Input: không nhận state; gọi `ps` hoặc PID cần kết thúc.
Output: process chuẩn hóa `(pid, name_lowercase)` hoặc thao tác kill.
Nguyên lý: giữ toàn bộ lệnh process Linux ở đây thay vì lặp trong feature.
"""

import os
import subprocess


class LinuxProcessOperations:
    """Thao tác process qua procps và POSIX signal."""

    def list_processes(self) -> list[tuple[int, str]]:
        """Đọc PID/name process từ `ps`; lỗi command trả danh sách rỗng."""

        try:
            output = subprocess.check_output(["ps", "-eo", "pid=,comm="], text=True)
        except (OSError, subprocess.SubprocessError):
            return []
        processes: list[tuple[int, str]] = []
        for line in output.splitlines():
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2 and parts[0].isdigit():
                processes.append((int(parts[0]), parts[1].lower()))
        return processes

    def kill_process(self, pid: int) -> None:
        """Kết thúc PID bằng SIGKILL như hành vi ProcessKiller cũ."""

        os.kill(pid, 9)
