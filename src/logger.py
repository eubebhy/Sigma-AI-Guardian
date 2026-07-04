"""Khung logger trung tam cua ung dung.

File path: `src/logger.py`
Input: `Path(__file__)` cua module can log va config tu `Config.getconfig()`.
Output: `logging.Logger` da gan formatter, file handler va ten logger theo module.
Nguyen ly: entry point goi `setup_log()` sau `setup_config()`; cac module goi
`Logger.registry(Path(__file__))` de lay logger rieng. Log tap trung vao
`logs/app.log`, loi tu `ERROR` tro len tach them vao `logs/error.log`, moi dong
co logger name, file path va line number de tail/trace nhanh.
"""

import logging
import sys
from pathlib import Path
from typing import ClassVar

from config import AppConfig, Config


LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | "
    "%(pathname)s:%(lineno)d | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class Logger:
    _is_setup: ClassVar[bool] = False
    _registered_names: ClassVar[set[str]] = set()

    @classmethod
    def setup(cls, config: AppConfig | None = None) -> None:
        active_config = config or Config.getconfig()
        active_config.logs_dir.mkdir(parents=True, exist_ok=True)

        root_logger = logging.getLogger()
        root_logger.setLevel(_log_level(active_config.log_level))
        root_logger.handlers.clear()

        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        app_log_path = active_config.logs_dir / active_config.log_file_name
        app_file_handler = logging.FileHandler(app_log_path, encoding="utf-8")
        app_file_handler.setLevel(_log_level(active_config.log_level))
        app_file_handler.setFormatter(formatter)
        root_logger.addHandler(app_file_handler)

        error_log_path = active_config.logs_dir / active_config.error_log_file_name
        error_file_handler = logging.FileHandler(error_log_path, encoding="utf-8")
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(formatter)
        root_logger.addHandler(error_file_handler)

        if active_config.log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(_log_level(active_config.log_level))
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        cls._is_setup = True

    @classmethod
    def registry(cls, module_file_path: str | Path) -> logging.Logger:
        if not cls._is_setup:
            cls.setup()

        logger_name = _module_logger_name(Path(module_file_path))
        cls._registered_names.add(logger_name)
        return logging.getLogger(logger_name)

    @classmethod
    def registered_names(cls) -> tuple[str, ...]:
        return tuple(sorted(cls._registered_names))


def setup_log(config: AppConfig | None = None) -> None:
    Logger.setup(config=config)


def _log_level(level_name: str) -> int:
    level = logging.getLevelName(level_name.upper())
    if isinstance(level, int):
        return level
    return logging.INFO


def _module_logger_name(module_file_path: Path) -> str:
    config = Config.getconfig()
    resolved_path = module_file_path.resolve()

    try:
        relative_path = resolved_path.relative_to(config.project_root)
    except ValueError:
        relative_path = resolved_path

    if relative_path.suffix == ".py":
        relative_path = relative_path.with_suffix("")

    return ".".join(relative_path.parts)
