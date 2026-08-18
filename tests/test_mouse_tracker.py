# pyright: reportPrivateUsage=false
"""Kiểm tra MouseTracker bằng backend fake, không đọc vị trí chuột thật."""

from __future__ import annotations

import contextlib
import io
import unittest
import threading
import sys
import time
from typing import cast
from unittest.mock import patch

from test_support import add_source_path, run_module


add_source_path()

from agent.platform_protocols import InputControllerOperations
from system_monitor.mouse_tracker import MouseTracker, run_real


class _FakeStopEvent:
    def __init__(self) -> None:
        self.wait_calls: list[float] = []

    def is_set(self) -> bool:
        return False

    def wait(self, timeout: float) -> bool:
        self.wait_calls.append(timeout)
        return len(self.wait_calls) == 2


class _FakeInputOperations:
    def __init__(self) -> None:
        self._positions = iter(((10, 20), (30, 40)))

    def position(self, take_new: bool = False) -> tuple[int, int]:
        self.assert_no_cached_position(take_new)
        return next(self._positions)

    def assert_no_cached_position(self, take_new: bool) -> None:
        if take_new:
            raise AssertionError("MouseTracker must read the current position")


class MouseTrackerTests(unittest.TestCase):
    def test_listen_records_positions_at_the_requested_interval(self) -> None:
        MouseTracker._positions.clear()
        stop_event = _FakeStopEvent()

        MouseTracker._listen(
            cast(threading.Event, stop_event),
            0.5,
            cast(InputControllerOperations, _FakeInputOperations()),
        )

        self.assertEqual(MouseTracker.get_current_positions(), [(10, 20), (30, 40)])
        self.assertEqual(stop_event.wait_calls, [0.5, 0.5])

    def test_listen_stores_backend_error(self) -> None:
        class _FailingInputOperations:
            def position(self, take_new: bool = False) -> tuple[int, int]:
                del take_new
                raise RuntimeError("position failed")

        MouseTracker._listener_error = None
        MouseTracker._listen(
            threading.Event(),
            0.5,
            cast(InputControllerOperations, _FailingInputOperations()),
        )

        self.assertEqual(str(MouseTracker.get_listener_error()), "position failed")
        with self.assertRaisesRegex(RuntimeError, "position failed"):
            MouseTracker.raise_if_listener_failed()


class MouseTrackerRealCommandTests(unittest.TestCase):
    def test_real_uses_interval_and_prints_positions(self) -> None:
        output = io.StringIO()
        positions = [(10, 20)]

        def get_positions() -> list[tuple[int, int]]:
            return positions

        with (
            patch.object(MouseTracker, "start") as start,
            patch.object(MouseTracker, "stop") as stop,
            patch.object(MouseTracker, "get_current_positions", side_effect=get_positions),
            patch.object(time, "sleep", side_effect=KeyboardInterrupt),
            contextlib.redirect_stdout(output),
        ):
            result = run_real(("0.67",))

        self.assertEqual(result, 0)
        start.assert_called_once_with(0.67)
        stop.assert_called_once_with()
        self.assertIn("Position: (10, 20)", output.getvalue())


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
