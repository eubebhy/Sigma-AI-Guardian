"""Entry point của SAG Agent.

File path: `src/main.py`.
Input: không có command.
Output: khởi tạo Agent.
"""

from agent import create_runtime
from logger import configure_logging
from logging import getLogger


def main() -> None:
    """Khởi tạo Agent."""
    configure_logging()
    create_runtime()


if __name__ == "__main__":
    logger = getLogger(__name__)
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Agent interrupted; stopping process")
    except Exception:
        logger.critical(
            "Agent failed with an unrecoverable error; stopping process",
            exc_info=True,
        )
