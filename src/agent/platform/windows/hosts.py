"""Adapter đường dẫn hosts Windows.

File path: `src/agent/platform/windows/hosts.py`.
Input: feature yêu cầu hosts path của platform hiện tại.
Output: đường dẫn hosts Windows.
Nguyên lý: feature web blocker không tự kiểm tra OS hoặc giữ đường dẫn native.
"""

from pathlib import Path


class WindowsHostsPathOperations:
    """Cung cấp đường dẫn hosts chuẩn trên Windows."""

    def get_hosts_path(self) -> Path:
        """Trả đường dẫn hosts. Quyền Administrator được kiểm tra lúc ghi."""

        return Path(r"C:\Windows\System32\drivers\etc\hosts")
