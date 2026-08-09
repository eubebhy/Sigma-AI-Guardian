# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""API chụp màn hình hiệu năng cao.

File path: `src/device_controller/screen_capture/__init__.py`
Input: `top`, `left`, `width`, `height` giống vùng monitor của MSS và
`sample_ratio` trong khoảng `(0.0, 1.0]`.
Output: `numpy.ndarray` dạng BGRA, `dtype=uint8`, tương tự raw frame MSS.
Nguyên lý: dùng MSS làm backend chụp cross-platform, giữ instance dùng lại để
tránh overhead và giảm mẫu khi `sample_ratio < 1.0` để nhẹ dữ liệu hơn.
"""

import atexit
import logging
import threading
from dataclasses import dataclass
from typing import Any, TypeAlias

import numpy as np
from mss import MSS
from mss.exception import ScreenShotError


logger = logging.getLogger(__name__)

Frame: TypeAlias = Any


@dataclass(frozen=True)
class ScreenRegion:
    """Vùng màn hình cần chụp theo format monitor của MSS."""

    top: int
    left: int
    width: int
    height: int
    sample_ratio: float = 1.0


# ScreenCapture là lớp trừu tượng hóa backend MSS, quản lý việc tái sử dụng
# instance, đồng bộ truy cập và lifecycle thay vì tách thành nhiều hàm nhỏ.
class ScreenCapture:
    """Giữ một MSS instance dùng lại để giảm overhead mỗi lần chụp."""

    def __init__(self) -> None:
        self._mss = MSS()
        self._lock = threading.Lock()

    def capture(
        self,
        top: int,
        left: int,
        width: int,
        height: int,
        sample_ratio: float = 1.0,
    ) -> Frame:
        """Chụp một vùng màn hình và trả về frame BGRA dạng numpy-compatible."""

        region = ScreenRegion(top=top, left=left, width=width, height=height)
        if not 0.0 < sample_ratio <= 1.0:
            raise ValueError("sample_ratio must be in range (0.0, 1.0]")

        monitor = {
            "top": region.top,
            "left": region.left,
            "width": region.width,
            "height": region.height,
        }
        with self._lock:
            shot = self._mss.grab(monitor)
        frame = np.asarray(shot, dtype=np.uint8)
        return _apply_sample_ratio(frame, sample_ratio)

    def close(self) -> None:
        """Đóng MSS backend nếu thư viện hiện tại hỗ trợ `close()`."""

        close = getattr(self._mss, "close", None)
        if callable(close):
            close()

    def get_monitors(self) -> list[ScreenRegion]:
        """Trả vùng của từng monitor vật lý theo tọa độ virtual desktop."""

        with self._lock:
            monitors = list(self._mss.monitors[1:])
        return [
            ScreenRegion(
                top=int(monitor["top"]),
                left=int(monitor["left"]),
                width=int(monitor["width"]),
                height=int(monitor["height"]),
            )
            for monitor in monitors
        ]


def capture(
    top: int,
    left: int,
    width: int,
    height: int,
    sample_ratio: float = 1.0,
) -> Frame:
    """Chụp bằng singleton backend và retry một lần nếu MSS lỗi."""

    global _capture_instance

    try:
        return _capture_instance.capture(
            top=top,
            left=left,
            width=width,
            height=height,
            sample_ratio=sample_ratio,
        )
    except ScreenShotError as error:
        logger.warning(
            "Screen capture backend thất bại với lỗi %s; tạo lại backend và retry",
            error,
        )
        _capture_instance = _create_capture_backend()
        return _capture_instance.capture(
            top=top,
            left=left,
            width=width,
            height=height,
            sample_ratio=sample_ratio,
        )


# Giữ facade module-level để caller và test có thể import/patch trực tiếp mà không
# cần biết singleton backend hoặc lifecycle nội bộ của ScreenCapture.
def get_monitors() -> list[ScreenRegion]:
    """Trả vùng của từng monitor vật lý cho các feature đa màn hình."""

    return _capture_instance.get_monitors()


def _apply_sample_ratio(frame: Frame, sample_ratio: float) -> Frame:
    if sample_ratio == 1.0:
        return frame
    step = max(1, round(1.0 / sample_ratio))
    return np.ascontiguousarray(frame[::step, ::step, :])


def _create_capture_backend() -> ScreenCapture:
    capture_backend = ScreenCapture()
    atexit.register(capture_backend.close)
    return capture_backend


_capture_instance: ScreenCapture = _create_capture_backend()

__all__ = ["ScreenCapture", "ScreenRegion", "capture", "get_monitors"]
