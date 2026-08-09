"""Adapter khởi chạy browser trên Linux.

File path: `src/agent/platform/linux/browser.py`.
Input: command browser đã được feature chọn.
Output: `True` nếu subprocess được tạo, `False` nếu hệ điều hành từ chối.
Nguyên lý: tách process browser khỏi Agent bằng session mới và bỏ output native.
"""

import os
import logging
import shutil
import subprocess
import webbrowser


logger = logging.getLogger(__name__)


class LinuxBrowserOperations:
    """Khởi chạy browser nền trên Linux."""

    def launch(self, command: list[str]) -> bool:
        """Tạo browser process không gắn stdout/stderr với Agent."""

        try:
            with open(os.devnull, "wb") as devnull:
                subprocess.Popen(
                    command,
                    stdout=devnull,
                    stderr=devnull,
                    start_new_session=True,
                )
            return True
        except OSError as error:
            logger.warning(
                "Linux browser could not launch command %s; returning False: %s",
                command,
                error,
            )
            return False

    def open_default_url(self, url: str) -> bool:
        """Mở URL qua browser mặc định của desktop Linux hiện tại."""

        return webbrowser.open(url, new=2)

    def find_executable(self, executables: tuple[str, ...]) -> str | None:
        """Tìm executable browser trong PATH của Linux."""

        for executable in executables:
            resolved = shutil.which(executable)
            if resolved is not None:
                return resolved
        return None
