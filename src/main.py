"""Entry point của SAG Agent.

File path: `src/main.py`.
Input: không có command.
Output: khởi tạo Agent và trả exit code.
"""

from agent import create_runtime
from logger import configure_logging


def main() -> int:
    """Khởi tạo Agent."""

    configure_logging()
    create_runtime()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
