"""Model trạng thái capability của SAG Agent.

File path: `src/agent/capabilities.py`.
Input: factory platform tạo các capability có tên và trạng thái khả dụng.
Output: `PlatformCapabilities` được CLI `status` hiển thị.
Nguyên lý: capability mô tả adapter có thể được chọn, không thay thế kiểm tra quyền
thực tế khi feature chạy.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    """Một khả năng của Agent cùng trạng thái khởi tạo."""

    name: str
    is_available: bool
    detail: str


@dataclass(frozen=True)
class PlatformCapabilities:
    """Tập capability cho đúng một Windows hoặc Linux runtime."""

    platform_name: str
    items: tuple[Capability, ...]

    def format_status(self) -> str:
        """Trả status text ổn định cho CLI và log caller."""

        lines = ["Sigma AI Guardian Agent", f"Platform: {self.platform_name}"]
        for item in self.items:
            state = "available" if item.is_available else "unavailable"
            lines.append(f"{item.name}: {state} ({item.detail})")
        return "\n".join(lines)
