"""API chụp màn hình hiệu năng cao.

File path: `src/device_controler/screen_capture/__init__.py`
Input: `top`, `left`, `width`, `height` giống vùng monitor của MSS và
`sharpness` trong khoảng `(0.0, 1.0]`.
Output: `numpy.ndarray` dạng BGRA, `dtype=uint8`, tương tự raw frame MSS.
Nguyên lý: dùng MSS làm backend chụp cross-platform, giữ instance dùng lại để
tránh overhead và giảm mẫu khi `sharpness < 1.0` để nhẹ dữ liệu hơn.
"""

from device_controler.screen_capture.capture import (
    ScreenCapture,
    ScreenRegion,
    capture,
    get_monitors,
)

__all__ = ["ScreenCapture", "ScreenRegion", "capture", "get_monitors"]
