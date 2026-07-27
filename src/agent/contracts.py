"""Contract giữa feature SAG Agent và adapter hệ điều hành.

File path: `src/agent/contracts.py`.
Input: adapter cung cấp process, browser và window theo các protocol ở đây.
Output: feature nhận dữ liệu chuẩn hóa, không phụ thuộc lệnh native từng OS.
Nguyên lý: contract chỉ mô tả capability nhỏ; nó không import adapter hay feature.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ProcessOperations(Protocol):
    """Liệt kê và kết thúc process theo format Agent thống nhất."""

    def list_processes(self) -> list[tuple[int, str]]:
        """Trả `(pid, process_name_lowercase)`; lỗi native được giữ nguyên."""

        ...

    def kill_process(self, pid: int) -> None:
        """Yêu cầu hệ điều hành kết thúc process theo PID và giữ nguyên lỗi native."""

        ...


class BrowserOperations(Protocol):
    """Khởi chạy browser mà không chặn Agent process."""

    def launch(self, command: list[str]) -> bool:
        """Trả `True` khi process browser được tạo thành công."""

        ...

    def open_default_url(self, url: str) -> bool:
        """Yêu cầu browser mặc định của platform mở URL hợp lệ."""

        ...

    def find_executable(self, executables: tuple[str, ...]) -> str | None:
        """Trả executable browser đầu tiên có thể chạy trên platform."""

        ...


class WindowOperations(Protocol):
    """Đọc title và process name của desktop hiện tại."""

    def get_active_window(self) -> tuple[str, str]:
        """Trả `(title, process_name)`, hoặc hai chuỗi rỗng nếu không có."""

        ...

    def get_open_windows(self) -> dict[str, str]:
        """Trả mapping title sang process name của cửa sổ đang mở."""

        ...


class HostsPathOperations(Protocol):
    """Cung cấp đường dẫn hosts của hệ điều hành hiện tại."""

    def get_hosts_path(self) -> Path:
        """Trả đường dẫn hosts chuẩn của platform."""

        ...
