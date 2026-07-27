# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportAttributeAccessIssue=false
"""Adapter truy vấn desktop Windows.

File path: `src/agent/platform/windows/windows.py`.
Input: không nhận tham số; đọc desktop qua PyWinCtl.
Output: title/process active hoặc mapping các cửa sổ đang mở.
Nguyên lý: mọi dependency window native Windows được cô lập tại adapter này.
"""

import pywinctl as pwc


class WindowsWindowOperations:
    """Đọc desktop Windows bằng PyWinCtl."""

    def get_active_window(self) -> tuple[str, str]:
        """Trả title/process active hoặc chuỗi rỗng nếu không có."""

        window = pwc.getActiveWindow()
        if window:
            return window.title, window.getAppName()
        return "", ""

    def get_open_windows(self) -> dict[str, str]:
        """Trả mapping title sang process name từ các cửa sổ hiện có."""

        return {
            window.title: window.getAppName()
            for window in pwc.getAllWindows()
        }
