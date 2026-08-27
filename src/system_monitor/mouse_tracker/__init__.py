"""Theo dõi vị trí con trỏ theo chu kỳ trong bộ nhớ.

File path: `src/system_monitor/mouse_tracker/__init__.py`.
Input: `start()` nhận khoảng lấy mẫu giây và adapter input tùy chọn.
Output: `get_current_positions()` trả danh sách tọa độ `(x, y)` theo thứ tự ghi nhận.
Nguyên lý: thread daemon đọc vị trí hiện tại mỗi chu kỳ và chỉ giữ queue trong bộ nhớ.

Lệnh manual: `./.pyvenv/bin/python tests/test_mouse_tracker.py real 0.67`.
"""

from __future__ import annotations

from collections import deque
import threading
import sys
import time
import traceback
from collections.abc import Sequence

from agent.platform import get_default_platform_services
from agent.platform_protocols import InputControllerOperations


class MouseTracker:
    """Giữ queue tọa độ con trỏ được lấy theo chu kỳ."""

    _listener: threading.Thread | None = None
    _listener_stop_event: threading.Event | None = None
    _listener_lock = threading.Lock()
    _listening = False
    _listener_error: Exception | None = None
    _positions: deque[tuple[int, int]] = deque()

    @classmethod
    def start(
        cls,
        interval: float = 1.0,
        operations: InputControllerOperations | None = None,
    ) -> None:
        """Bắt đầu lấy vị trí con trỏ theo `interval` giây."""

        if interval <= 0:
            raise ValueError("Interval must be greater than zero")
        with cls._listener_lock:
            if cls._listener is not None and cls._listener.is_alive():
                return
            cls._listener_error = None
            cls._listening = True
            cls._listener_stop_event = threading.Event()
            cls._listener = threading.Thread(
                target=cls._listen,
                args=(cls._listener_stop_event, interval, operations),
                daemon=True,
            )
            cls._listener.start()

    @classmethod
    def stop(cls) -> None:
        """Dừng theo dõi và xóa các tọa độ đã lưu."""

        with cls._listener_lock:
            cls._listening = False
            stop_event = cls._listener_stop_event
            listener = cls._listener
            if stop_event is not None:
                stop_event.set()
        if listener is not None and listener is not threading.current_thread():
            listener.join()
        with cls._listener_lock:
            cls._positions.clear()

    @classmethod
    def _listen(
        cls,
        stop_event: threading.Event,
        interval: float,
        operations: InputControllerOperations | None,
    ) -> None:
        input_operations = operations or get_default_platform_services().input_controller
        try:
            while not stop_event.is_set():
                position = input_operations.position()
                with cls._listener_lock:
                    cls._positions.append(position)
                if stop_event.wait(interval):
                    break
        except Exception as error:
            cls._listener_error = error
        finally:
            with cls._listener_lock:
                cls._listening = False
                if cls._listener_stop_event is stop_event:
                    cls._listener_stop_event = None
                    cls._listener = None

    @classmethod
    def get_current_positions(cls) -> list[tuple[int, int]]:
        """Trả bản sao queue tọa độ hiện tại, không xóa state."""

        with cls._listener_lock:
            return list(cls._positions)

    @classmethod
    def get_listener_error(cls) -> Exception | None:
        """Trả lỗi backend đã lưu trong lúc theo dõi."""

        return cls._listener_error

    @classmethod
    def raise_if_listener_failed(cls) -> None:
        """Ném lại lỗi backend đã lưu để caller xử lý."""

        if cls._listener_error is not None:
            raise cls._listener_error


def _parse_real_interval(arguments: Sequence[str]) -> float | None:
    if len(arguments) != 1:
        return None
    try:
        interval = float(arguments[0])
    except ValueError:
        return None
    return interval if interval > 0 else None


def run_real(arguments: Sequence[str]) -> int:
    """Theo dõi và in vị trí chuột thật đến khi caller nhấn Ctrl+C."""

    interval = _parse_real_interval(arguments)
    if interval is None:
        print("Usage: real INTERVAL", file=sys.stderr)
        return 2
    try:
        MouseTracker.start(interval)
        print("Tracking cursor position. Press Ctrl+C to stop.", flush=True)
        printed_count = 0
        while True:
            MouseTracker.raise_if_listener_failed()
            positions = MouseTracker.get_current_positions()
            for position in positions[printed_count:]:
                print(f"Position: {position}", flush=True)
            printed_count = len(positions)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Tracking stopped.", flush=True)
        return 0
    except Exception as error:
        print(f"Mouse tracker failed: {error}", file=sys.stderr)
        traceback.print_exc()
        return 1
    finally:
        MouseTracker.stop()


__all__ = ["MouseTracker", "run_real"]
