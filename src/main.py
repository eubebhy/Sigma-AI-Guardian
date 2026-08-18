"""Entry point của SAG Agent.

File path: `src/main.py`.
Input: không có command.
Output: khởi tạo Agent.
"""

from agent import create_runtime
from config import AgentConfig
from logger import configure_logging
from logging import getLogger
from paths import get_agent_paths


def main() -> None:
    """Khởi tạo Agent."""
    configure_logging()
    paths = get_agent_paths()
    config = AgentConfig()
    config.load(
        primary_path=paths.config_path,
        last_good_path=paths.last_good_config_path,
        fallback_path=paths.fallback_config_path,
    )
    runtime = create_runtime(config=config)
    try:
        runtime.start()
    finally:
        runtime.shutdown()


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
