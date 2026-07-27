"""Adapter khởi chạy browser trên Windows.

File path: `src/agent/platform/windows/browser.py`.
Input: command browser đã được feature chọn.
Output: `True` nếu subprocess được tạo, `False` nếu hệ điều hành từ chối.
Nguyên lý: tạo process group riêng để browser không chặn Agent process.
"""

import subprocess
import shutil
import webbrowser


class WindowsBrowserOperations:
    """Khởi chạy browser nền trên Windows."""

    def launch(self, command: list[str]) -> bool:
        """Tạo browser process group như hành vi mở tab cũ."""

        try:
            subprocess.Popen(command, creationflags=0x00000200)
            return True
        except OSError:
            return False

    def open_default_url(self, url: str) -> bool:
        """Mở URL qua browser mặc định của desktop Windows hiện tại."""

        return webbrowser.open(url, new=2)

    def find_executable(self, executables: tuple[str, ...]) -> str | None:
        """Tìm executable browser trong PATH của Windows."""

        for executable in executables:
            resolved = shutil.which(executable)
            if resolved is not None:
                return resolved
        return None
