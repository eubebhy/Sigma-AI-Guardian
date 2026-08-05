"""API theo dõi cửa sổ desktop cho SAG Agent.

File path: `src/system_monitor/window_tracker/__init__.py`.
Input: không nhận tham số; caller có thể truyền adapter `WindowOperations` khi test.
Output: tiêu đề active hoặc mapping tiêu đề sang process name của cửa sổ đang mở.
Nguyên lý: feature chỉ gọi contract Agent; PyWinCtl và fallback xdotool nằm trong
adapter Windows/Linux tương ứng.
"""

from agent.contracts import WindowOperations
from agent.platform import get_default_platform_services


def _get_operations(operations: WindowOperations | None) -> WindowOperations:
    if operations is not None:
        return operations
    return get_default_platform_services().windows


def get_active_window_name(
    operations: WindowOperations | None = None,
) -> tuple[str, str]:
    """Trả title/process active, hoặc hai chuỗi rỗng khi desktop không có cửa sổ."""

    return _get_operations(operations).get_active_window()


def get_all_open_windows(
    operations: WindowOperations | None = None,
) -> dict[str, str]:
    """Trả mapping title sang process name của cửa sổ đang mở."""

    return _get_operations(operations).get_open_windows()
