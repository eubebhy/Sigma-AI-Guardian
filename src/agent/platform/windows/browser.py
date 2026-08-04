"""Adapter khởi chạy browser trên Windows.

File path: `src/agent/platform/windows/browser.py`.
Input: command browser đã được feature chọn.
Output: `True` nếu subprocess được tạo, `False` nếu hệ điều hành từ chối.
Nguyên lý: tạo process group riêng để browser không chặn Agent process.
"""

import logging
import subprocess
import shutil
import webbrowser


logger = logging.getLogger(__name__)


class WindowsBrowserOperations:
    """Khởi chạy browser nền trên Windows."""

    def launch(self, command: list[str]) -> bool:
        """Tạo browser process group như hành vi mở tab cũ."""

        try:
            subprocess.Popen(command, creationflags=0x00000200)
            return True
        except OSError as error:
            logger.info("Windows browser launch failed for %r: %s", command, error)
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
