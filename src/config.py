"""Khung config trung tam cua ung dung.

File path: `src/config.py`
Input: file JSON tuy chon `config.json` o project root, hoac dict override khi test.
Output: object `AppConfig` dung chung cho cac module.
Nguyen ly: entry point goi `setup_config()` truoc; cac module khac chi goi
`Config.getconfig()` de lay config da duoc validate va fallback san.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"


@dataclass(frozen=True)
class AppConfig:
    project_root: Path
    logs_dir: Path
    log_level: str
    log_file_name: str
    error_log_file_name: str
    log_to_console: bool
    config_path: Path | None


class Config:
    _config: ClassVar[AppConfig | None] = None

    @classmethod
    def setup(
        cls,
        config_path: str | Path | None = None,
        overrides: dict[str, object] | None = None,
    ) -> AppConfig:
        selected_config_path = Path(config_path) if config_path is not None else None
        raw_config = _read_config_file(selected_config_path or DEFAULT_CONFIG_PATH)
        if overrides is not None:
            raw_config.update(overrides)

        config = _build_config(raw_config, selected_config_path)
        config.logs_dir.mkdir(parents=True, exist_ok=True)
        cls._config = config
        return config

    @classmethod
    def getconfig(cls) -> AppConfig:
        if cls._config is None:
            return cls.setup()
        return cls._config


def setup_config(
    config_path: str | Path | None = None,
    overrides: dict[str, object] | None = None,
) -> AppConfig:
    return Config.setup(config_path=config_path, overrides=overrides)


def _read_config_file(config_path: Path) -> dict[str, object]:
    if not config_path.exists():
        return {}

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if isinstance(data, dict):
        return {str(key): value for key, value in data.items()}
    return {}


def _build_config(
    raw_config: dict[str, object],
    selected_config_path: Path | None,
) -> AppConfig:
    project_root_config = raw_config.get("project_root")
    if isinstance(project_root_config, str) and project_root_config.strip():
        project_root = Path(project_root_config).expanduser()
    elif isinstance(project_root_config, Path):
        project_root = project_root_config.expanduser()
    else:
        project_root = PROJECT_ROOT

    logs_dir_config = raw_config.get("logs_dir")
    if isinstance(logs_dir_config, str) and logs_dir_config.strip():
        logs_dir = Path(logs_dir_config).expanduser()
    elif isinstance(logs_dir_config, Path):
        logs_dir = logs_dir_config.expanduser()
    else:
        logs_dir = project_root / "logs"

    if not logs_dir.is_absolute():
        logs_dir = project_root / logs_dir

    log_level_config = raw_config.get("log_level")
    log_file_name_config = raw_config.get("log_file_name")
    error_log_file_name_config = raw_config.get("error_log_file_name")
    log_to_console_config = raw_config.get("log_to_console")

    return AppConfig(
        project_root=project_root,
        logs_dir=logs_dir,
        log_level=(
            log_level_config.strip().upper()
            if isinstance(log_level_config, str) and log_level_config.strip()
            else "INFO"
        ),
        log_file_name=(
            log_file_name_config.strip()
            if isinstance(log_file_name_config, str) and log_file_name_config.strip()
            else "app.log"
        ),
        error_log_file_name=(
            error_log_file_name_config.strip()
            if isinstance(error_log_file_name_config, str)
            and error_log_file_name_config.strip()
            else "error.log"
        ),
        log_to_console=(
            log_to_console_config if isinstance(log_to_console_config, bool) else True
        ),
        config_path=selected_config_path or DEFAULT_CONFIG_PATH,
    )
