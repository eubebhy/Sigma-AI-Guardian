"""Entry point CLI tối thiểu của SAG Agent.

File path: `src/main.py`.
Input: command `status` hoặc không có command từ command line.
Output: in trạng thái platform Agent; trả exit code 0 khi thành công.
Nguyên lý: file chỉ parse CLI và giao bootstrap cho `agent.runtime`; nó không gọi
feature hay API hệ điều hành trực tiếp.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import logging

from agent.runtime import create_runtime
from logger import configure_logging


logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sigma AI Guardian Agent")
    parser.add_argument("command", choices=("status",), nargs="?", default="status")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Chạy command Agent an toàn hiện có."""

    configure_logging()
    logger.info("Starting main process")
    arguments = _build_parser().parse_args(argv)
    logger.info("Creating runtime")
    runtime = create_runtime()
    logger.info("Created runtime")
    try:
        if arguments.command == "status":
            print(runtime.status())
            logger.info("Status command completed")
            return 0
        return 1
    finally:
        runtime.shutdown()
        logger.info("Main process shutdown completed")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        logger.info("Main process interrupted by user")
        print("Exiting...")

    except Exception:
        logger.critical("Main process failed", exc_info=True)
        raise SystemExit(1)
