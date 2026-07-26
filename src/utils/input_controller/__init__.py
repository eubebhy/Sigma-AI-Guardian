"""API gửi input độc lập hệ điều hành theo tập con tương thích PyAutoGUI.

File path: `src/utils/input_controller/__init__.py`.
Input: lời gọi gửi keyboard hoặc mouse với tham số theo PyAutoGUI.
Output: bảy hàm public của backend phù hợp với hệ điều hành đang chạy.
Nguyên lý: facade chọn Linux hoặc Windows lúc import; mỗi backend tự nạp dependency
khi cần gửi event. Listener được giữ trong các module backend riêng.
"""

import sys

if sys.platform == "win32":
    from utils.input_controller.window import (
        click,
        keyDown,
        keyUp,
        moveRel,
        moveTo,
        press,
        write,
    )
else:
    from utils.input_controller.linux import (
        click,
        keyDown,
        keyUp,
        moveRel,
        moveTo,
        press,
        write,
    )


__all__ = ["click", "keyDown", "keyUp", "moveRel", "moveTo", "press", "write"]
