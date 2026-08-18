"""Xác định các path mặc định của SAG Agent.

File path: `src/paths.py`.
Input: platform tùy chọn để test.
Output: `AgentPaths` chứa các path config, data và log.
Nguyên lý: chỉ tạo đối tượng `Path`, không tạo thư mục hoặc ghi file.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import sys


@dataclass(frozen=True)
class AgentPaths:
    """Các path dùng chung của một Agent process."""

    config_path: Path
    last_good_config_path: Path
    fallback_config_path: Path
    data_dir: Path
    log_dir: Path


def get_agent_paths(platform_name: str | None = None) -> AgentPaths:
    """Trả về path mặc định theo platform hiện tại."""

    platform = (platform_name or sys.platform).lower()
    if platform.startswith("win"):
        # Config: %APPDATA%/Sigma-AI-Guardian/
        config_root = (
            Path(os.environ.get("APPDATA", "C:/Users/Public/AppData/Roaming"))
            / "Sigma-AI-Guardian"
        )

        # Data: %LOCALAPPDATA%/Sigma-AI-Guardian/
        data_root = (
            Path(os.environ.get("LOCALAPPDATA", "C:/Users/Public/AppData/Local"))
            / "Sigma-AI-Guardian"
        )

        # Log: %LOCALAPPDATA%/Sigma-AI-Guardian/logs/
        log_root = data_root / "logs"
    elif platform.startswith("linux"):
        # Config: $XDG_CONFIG_HOME/sigma-ai-guardian/
        # Default: ~/.config/sigma-ai-guardian/
        config_root = (
            Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
            / "sigma-ai-guardian"
        )

        # Data: $XDG_DATA_HOME/sigma-ai-guardian/
        # Default: ~/.local/share/sigma-ai-guardian/
        data_root = (
            Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser()
            / "sigma-ai-guardian"
        )

        # Log: $XDG_STATE_HOME/sigma-ai-guardian/
        # Default: ~/.local/state/sigma-ai-guardian/
        log_root = (
            Path(os.environ.get("XDG_STATE_HOME", "~/.local/state")).expanduser()
            / "sigma-ai-guardian"
        )
    else:
        raise ValueError(f"Unsupported platform: {platform}")

    # Config file: <config_root>/sag-agent-config.toml
    return AgentPaths(
        config_path=config_root / "sag-agent-config.toml",
        # Last-good config: <config_root>/sag-agent-config.last-good.toml
        last_good_config_path=config_root / "sag-agent-config.last-good.toml",
        # Fallback config: <config_root>/sag-agent-config.fallback.toml
        fallback_config_path=config_root / "sag-agent-config.fallback.toml",
        data_dir=data_root,
        log_dir=log_root,
    )
