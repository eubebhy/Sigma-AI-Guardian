"""Khóa màn hình thật để kiểm tra thủ công screen locker.

File path: `tests/screen_locker.py`.
Input: `--delay` là thời gian chờ trước khi khóa; `--seconds` là thời gian khóa.
Output: in trạng thái ra terminal, khóa thật, rồi tự mở khóa sau thời lượng chọn.
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _non_negative_seconds(value: str) -> float:
    seconds = float(value)
    if seconds < 0:
        raise argparse.ArgumentTypeError("seconds must be non-negative")
    return seconds


def _build_parser() -> argparse.ArgumentParser:
    """Tạo CLI cho thời điểm khóa và thời lượng khóa thật."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=_non_negative_seconds, default=5.0)
    parser.add_argument("--seconds", type=_non_negative_seconds, default=20.0)
    return parser


def _run_lock_test(delay: float, seconds: float) -> None:
    """Chờ, khóa thật trong thời lượng yêu cầu rồi luôn mở khóa."""

    from device_controler.screenlocker import lock, unlock

    print(f"Screen locks in {delay:g} seconds.")
    time.sleep(delay)
    print(f"Screen locked for {seconds:g} seconds.")
    unlock_timer: threading.Timer | None = None
    try:
        lock()
        unlock_timer = threading.Timer(seconds, unlock)
        unlock_timer.start()
        time.sleep(seconds)
    finally:
        if unlock_timer is not None:
            unlock_timer.cancel()
        unlock()
    print("Screen unlocked.")


def main() -> None:
    """Chạy vòng đời kiểm thử screen locker thật."""

    arguments = _build_parser().parse_args()
    _run_lock_test(arguments.delay, arguments.seconds)


if __name__ == "__main__":
    main()
