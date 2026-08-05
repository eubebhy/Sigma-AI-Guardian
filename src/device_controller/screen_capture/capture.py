# pyright: reportMissingImports=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Wrapper chup man hinh bang MSS.

File path: `src/device_controller/screen_capture/capture.py`
Input contract:
- capture(top, left, width, height, sample_ratio): toa do/vung chup kieu MSS.
- sample_ratio trong khoang `(0.0, 1.0]`.
Output contract:
- Tra ve frame BGRA, dtype uint8, theo raw buffer cua MSS.
- Khi sample_ratio < 1.0, frame nho hon theo ti le lay mau.
Operating principle:
- Giu mot MSS instance dung lai trong process.
- Moi lan chup lay raw BGRA roi giam mau bang numpy slicing.
- Neu backend MSS loi thi tao lai backend va chup lai mot lan.
"""

from __future__ import annotations

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
        """Trả các monitor vật lý theo tọa độ virtual desktop của MSS."""

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
    """API tiện ích dùng singleton backend và tự tạo lại một lần khi MSS lỗi."""

    global _capture_instance

    try:
        return _capture_instance.capture(
            top=top,
            left=left,
            width=width,
            height=height,
            sample_ratio=sample_ratio,
        )
    except ScreenShotError:
        logger.warning("Screen capture backend failed; recreating backend and retrying")
        _capture_instance = _create_capture_backend()
        return _capture_instance.capture(
            top=top,
            left=left,
            width=width,
            height=height,
            sample_ratio=sample_ratio,
        )


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
