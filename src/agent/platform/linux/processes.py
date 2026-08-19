"""Adapter process Linux của SAG Agent.

File path: `src/agent/platform/linux/processes.py`.
Input: không nhận state; gọi `ps` hoặc PID cần kết thúc.
Output: process chuẩn hóa `(pid, name_lowercase)` hoặc thao tác kill.
Nguyên lý: giữ toàn bộ lệnh process Linux ở đây thay vì lặp trong feature.
"""

import os
import subprocess

LINUX_PROTECTED_PROCESSES = [
    # systemd / core session
    "systemd",
    "systemd-logind",
    "systemd-resolved",
    "systemd-journald",
    "systemd-udevd",
    "systemd-timesyncd",
    # IPC / authorization / hardware
    "dbus-daemon",
    "dbus-broker",
    "polkitd",
    "udisksd",
    "upowerd",
    # Network
    "NetworkManager",
    "wpa_supplicant",
    # GNOME
    "gnome-shell",
    "gnome-session",
    "gnome-settings-daemon",
    "gnome-keyring-daemon",
    "xdg-desktop-portal",
    "xdg-desktop-portal-gnome",
    # KDE Plasma
    "plasmashell",
    "kwin_wayland",
    "kwin_x11",
    "kded5",
    "kded6",
    "kglobalacceld",
    "xdg-desktop-portal-kde",
    # Audio / desktop basics
    "pipewire",
    "wireplumber",
    "pulseaudio",
]


class LinuxProcessOperations:
    """Thao tác process qua procps và POSIX signal."""

    def list_processes(self) -> list[tuple[int, str]]:
        """Đọc PID/name process từ `ps`; lỗi command được giữ nguyên cho caller."""

        output = subprocess.check_output(["ps", "-eo", "pid=,comm="], text=True)
        processes: list[tuple[int, str]] = []
        for line in output.splitlines():
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2 and parts[0].isdigit():
                processes.append((int(parts[0]), parts[1].lower()))
        return processes

    def kill_process(self, pid: int) -> None:
        """Kết thúc PID bằng SIGKILL như hành vi ProcessKiller cũ."""

        os.kill(pid, 9)

    def list_system_processes(self) -> list[str]:
        return LINUX_PROTECTED_PROCESSES
