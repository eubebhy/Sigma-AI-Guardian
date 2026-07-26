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

from agent.runtime import create_runtime


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sigma AI Guardian Agent")
    parser.add_argument("command", choices=("status",), nargs="?", default="status")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Chạy command Agent an toàn hiện có."""

    arguments = _build_parser().parse_args(argv)
    runtime = create_runtime()
    try:
        if arguments.command == "status":
            print(runtime.status())
            return 0
        return 1
    finally:
        runtime.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
