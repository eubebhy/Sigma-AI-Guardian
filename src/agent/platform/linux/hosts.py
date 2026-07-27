"""Adapter đường dẫn hosts Linux.

File path: `src/agent/platform/linux/hosts.py`.
Input: feature yêu cầu hosts path của platform hiện tại.
Output: `/etc/hosts`.
Nguyên lý: feature web blocker không tự kiểm tra OS hoặc giữ đường dẫn native.
"""

from pathlib import Path


class LinuxHostsPathOperations:
    """Cung cấp đường dẫn hosts chuẩn trên Linux."""

    def get_hosts_path(self) -> Path:
        """Trả `/etc/hosts`. Quyền ghi được kiểm tra lúc feature sử dụng."""

        return Path("/etc/hosts")
