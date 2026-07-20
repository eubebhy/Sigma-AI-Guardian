"""CLI ghi lại keyboard và mouse event thật trên Linux.

File path: `tests/input_controller/kb_mouse_event_logger.py`
Input: `--kb`, `--mouse` hoặc cả hai; đọc `/dev/input/event*` qua listener.
Output: liên tục in event đã chuẩn hóa cho đến khi người dùng nhấn Ctrl+C.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from threading import Thread

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from utils.input_controller.linux import listen_keys, listen_mice


def _log_kb() -> None:
    for event in listen_keys():
        print("kb:", event, flush=True)


def _log_mouse() -> None:
    for event in listen_mice():
        print("mouse:", event, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Log Linux keyboard/mouse events.")
    parser.add_argument("--kb", action="store_true", help="Log keyboard events.")
    parser.add_argument("--mouse", action="store_true", help="Log mouse events.")
    args = parser.parse_args()
    if not args.kb and not args.mouse:
        parser.error("at least one of --kb or --mouse is required")

    print("Logging events. Press Ctrl+C to stop.")
    if args.kb and args.mouse:
        Thread(target=_log_kb, daemon=True).start()
        _log_mouse()
    elif args.kb:
        _log_kb()
    else:
        _log_mouse()


if __name__ == "__main__":
    main()
