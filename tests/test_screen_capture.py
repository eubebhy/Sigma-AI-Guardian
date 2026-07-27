# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Kiểm thử API monitor an toàn và benchmark capture ở mode real.

File path: ``tests/test_screen_capture.py``.
Input: safe suite không chụp desktop; manual benchmark nhận ``SECONDS`` dương và
``SHARPNESS`` trong ``(0.0, 1.0]``.
Output: benchmark in FPS cho từng resolution chuẩn vừa màn hình hiện tại.
Nguyên lý: chỉ ``real benchmark`` gọi MSS và API capture thật.

Lệnh manual chính xác: ``./.pyvenv/bin/python tests/test_screen_capture.py real
benchmark 3 1.0``.
Preflight/prerequisites: chạy trong desktop session có màn hình và MSS hỗ trợ; đóng
ứng dụng hiển thị dữ liệu nhạy cảm nếu không muốn chúng bị capture trong bộ nhớ.
Side effect: đọc frame desktop thật, không ghi file hay thay đổi hệ thống. Ctrl+C
dừng benchmark ngay; không có tài nguyên capture nào được giữ bởi runner.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
import time
import unittest
from collections.abc import Sequence
from typing import NoReturn

from mss import mss

from test_support import add_source_path, run_module, test_modes


add_source_path()

from device_controler import screen_capture


@dataclass(frozen=True)
class _BenchmarkCase:
    width: int
    height: int


_DEFAULT_RESOLUTIONS: tuple[_BenchmarkCase, ...] = (
    _BenchmarkCase(640, 360),
    _BenchmarkCase(1280, 720),
    _BenchmarkCase(1600, 900),
    _BenchmarkCase(1920, 1080),
    _BenchmarkCase(2560, 1440),
    _BenchmarkCase(3440, 1440),
    _BenchmarkCase(3840, 2160),
    _BenchmarkCase(5120, 2880),
    _BenchmarkCase(7680, 4320),
)


class _RealArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _parse_real_arguments(arguments: Sequence[str]) -> argparse.Namespace | None:
    parser = _RealArgumentParser(add_help=False)
    commands = parser.add_subparsers(dest="command", required=True)
    benchmark = commands.add_parser("benchmark", add_help=False)
    benchmark.add_argument("seconds", type=float)
    benchmark.add_argument("sharpness", type=float)
    try:
        command = parser.parse_args(arguments)
    except (argparse.ArgumentError, ValueError):
        return None
    if command.seconds <= 0.0 or not 0.0 < command.sharpness <= 1.0:
        return None
    return command


def _screen_size() -> _BenchmarkCase:
    with mss() as capture_backend:
        monitor = capture_backend.monitors[0]
    return _BenchmarkCase(width=int(monitor["width"]), height=int(monitor["height"]))


def _valid_cases(screen_size: _BenchmarkCase) -> list[_BenchmarkCase]:
    return [
        case
        for case in _DEFAULT_RESOLUTIONS
        if case.width <= screen_size.width and case.height <= screen_size.height
    ]


def _benchmark_case(case: _BenchmarkCase, seconds: float, sharpness: float) -> float:
    started_at = time.perf_counter()
    frames = 0
    while time.perf_counter() - started_at < seconds:
        screen_capture.capture(0, 0, case.width, case.height, sharpness)
        frames += 1
    elapsed = time.perf_counter() - started_at
    return frames / elapsed if elapsed > 0.0 else 0.0


def _run_benchmark(cases: list[_BenchmarkCase], seconds: float, sharpness: float) -> None:
    for case in cases:
        frames_per_second = _benchmark_case(case, seconds, sharpness)
        print(f"{case.width}x{case.height}: {frames_per_second:.2f} FPS")


def run_real(arguments: Sequence[str]) -> int:
    """Chạy benchmark capture có chủ đích, không được gọi bởi safe suite."""

    command = _parse_real_arguments(arguments)
    if command is None:
        print("Usage: real benchmark SECONDS SHARPNESS", file=sys.stderr)
        return 2
    try:
        cases = _valid_cases(_screen_size())
        if not cases:
            print("No standard resolution is valid for the current screen", file=sys.stderr)
            return 1
        _run_benchmark(cases, command.seconds, command.sharpness)
    except KeyboardInterrupt:
        print("Benchmark interrupted")
        return 130
    except Exception as error:
        print(f"Benchmark failed: {error}", file=sys.stderr)
        return 1
    return 0


class ScreenCaptureTests(unittest.TestCase):
    """Screen capture có API monitor và benchmark thật riêng biệt."""

    @test_modes("fake", "smoke")
    def test_exports_monitor_regions(self) -> None:
        self.assertTrue(hasattr(screen_capture, "get_monitors"))

    @test_modes("fake")
    def test_valid_cases_excludes_larger_resolutions(self) -> None:
        cases = _valid_cases(_BenchmarkCase(width=1280, height=720))

        self.assertEqual(cases, [_BenchmarkCase(640, 360), _BenchmarkCase(1280, 720)])

    @test_modes("real")
    def test_capture_benchmark(self) -> None:
        cases = _valid_cases(_screen_size())
        self.assertTrue(cases, "No standard resolution is valid for the current screen")
        _run_benchmark(cases, seconds=3.0, sharpness=1.0)


class RealScreenCaptureCommandTests(unittest.TestCase):
    def test_parse_real_benchmark_command(self) -> None:
        command = _parse_real_arguments(("benchmark", "2.5", "0.75"))

        self.assertIsNotNone(command)
        assert command is not None
        self.assertEqual(command.command, "benchmark")
        self.assertEqual(command.seconds, 2.5)
        self.assertEqual(command.sharpness, 0.75)

    def test_parse_real_benchmark_rejects_invalid_values(self) -> None:
        self.assertIsNone(_parse_real_arguments(("benchmark", "0", "1.0")))
        self.assertIsNone(_parse_real_arguments(("benchmark", "1", "1.1")))


if __name__ == "__main__":
    raise SystemExit(run_module(sys.modules[__name__]))
