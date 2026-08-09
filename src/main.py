"""Entry point của SAG Agent.

File path: `src/main.py`.
Input: không có command.
Output: khởi tạo Agent và trả exit code.
"""

from agent import AgentRuntime, create_runtime
from logger import configure_logging
from logging import getLogger


def main() -> int:
    """Khởi tạo Agent."""
    logger = getLogger(__name__)
    agent: AgentRuntime | None = None

    try:
        configure_logging()
        agent = create_runtime()
        return 0

    except KeyboardInterrupt:
        logger.info("Agent interrupted; starting shutdown")
        if agent is not None:
            agent.shutdown()
        return 0

    except Exception:
        logger.critical(
            "Agent gặp lỗi không thể khắc phục; process sẽ kết thúc",
            exc_info=True,
        )
        if agent is not None:
            agent.shutdown()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
