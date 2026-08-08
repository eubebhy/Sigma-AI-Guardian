"""Đọc, kiểm tra và giữ cấu hình runtime của SAG Agent.

File path: `src/config.py`.
Input: primary, last-known-good và fallback TOML.
Output: `config.<section>.<field>` sau khi `AgentConfig.load()` hoàn tất.

Kiến trúc:
- `fallback_path` là schema bắt buộc: phải có đúng mọi section/field và type.
- Với từng field runtime, `load()` ưu tiên primary, last-good rồi fallback.
- Primary chỉ được ghi thành last-good khi toàn bộ file khớp schema fallback.
"""

from dataclasses import dataclass
from pathlib import Path
import shutil
import tomllib
from typing import Any, cast, get_args, get_origin, get_type_hints


# Config errors
class ConfigError(Exception):
    """Lỗi gốc của hệ thống config."""


class ConfigFileError(ConfigError):
    """Không thể đọc file config."""


class ConfigFormatError(ConfigError):
    """Nội dung TOML không hợp lệ."""


class ConfigSchemaError(ConfigError):
    """Section hoặc key config không khớp schema."""


class ConfigTypeError(ConfigError):
    """Giá trị config không đúng type."""


# Shared section validation
class _ConfigSection:
    """Base class kiểm tra type của từng field config."""

    def __post_init__(self) -> None:
        type_hints = get_type_hints(type(self))
        for name, value in vars(self).items():
            if not _matches_type(value, type_hints[name]):
                raise ConfigTypeError(
                    f"{type(self).__name__}.{name} has invalid type: {value!r}"
                )


def _matches_type(value: object, expected_type: object) -> bool:
    if get_origin(expected_type) is list:
        item_type = get_args(expected_type)[0]
        return isinstance(value, list) and all(
            type(item) is item_type for item in cast(list[object], value)
        )
    return isinstance(expected_type, type) and type(value) is expected_type


# TOML section config objects
@dataclass(frozen=True)
class SystemConfig(_ConfigSection):
    config_update_check_interval_seconds: float


@dataclass(frozen=True)
class WebBlockerConfig(_ConfigSection):
    enabled: bool
    block_game: bool
    block_gore: bool
    block_porn: bool
    block_social: bool
    block_messaging: bool
    block_entertainment: bool
    custom_allowlist: list[str]
    custom_blocklist: list[str]


@dataclass(frozen=True)
class ProcessGuardConfig(_ConfigSection):
    enabled: bool
    scan_interval_seconds: float
    blocked_processes: list[str]


@dataclass(frozen=True)
class WindowMonitorConfig(_ConfigSection):
    enabled: bool
    scan_interval_seconds: float
    scope: str


@dataclass(frozen=True)
class ClassifierConfig(_ConfigSection):
    enabled: bool
    default_strictness: str


@dataclass(frozen=True)
class ScreenMonitorConfig(_ConfigSection):
    max_fps_scale: float
    max_fps: float
    min_fps: float


@dataclass(frozen=True)
class ScreenLockConfig(_ConfigSection):
    message: str


_SECTION_TYPES: dict[str, type[_ConfigSection]] = {
    "system": SystemConfig,
    "web_blocker": WebBlockerConfig,
    "process_guard": ProcessGuardConfig,
    "window_monitor": WindowMonitorConfig,
    "classifier": ClassifierConfig,
    "screen_monitor": ScreenMonitorConfig,
    "screen_lock": ScreenLockConfig,
}

_SECTION_FIELD_TYPES: dict[str, dict[str, object]] = {
    section_name: get_type_hints(config_type)
    for section_name, config_type in _SECTION_TYPES.items()
}


# Combined Agent config
class AgentConfig:
    """Giữ config hiện tại; section là `None` trước lần load đầu tiên."""

    __slots__ = tuple(_SECTION_TYPES)

    def __init__(self) -> None:
        for section_name in _SECTION_TYPES:
            object.__setattr__(self, section_name, None)

    def __setattr__(self, name: str, value: object, /) -> None:
        raise ConfigError("Use AgentConfig.load() to update config")

    def load(
        self,
        primary_path: str | Path,
        last_good_path: str | Path,
        fallback_path: str | Path,
    ) -> None:
        """Load từng field theo thứ tự primary, last-good rồi fallback."""

        primary_data = _try_read_toml(primary_path)
        last_good_data = _try_read_toml(last_good_path)
        fallback_data = _read_required_toml(fallback_path)
        _validate_complete_config(fallback_data)

        new_values: dict[str, _ConfigSection] = {}
        for section_name, config_type in _SECTION_TYPES.items():
            new_values[section_name] = _load_section(
                section_name,
                config_type,
                primary_data,
                last_good_data,
                fallback_data,
            )

        for section_name, value in new_values.items():
            object.__setattr__(self, section_name, value)

        if _is_complete_valid_config(primary_data):
            _save_last_good(primary_path, last_good_path)


# Per-field source selection
def _load_section(
    section_name: str,
    config_type: type[_ConfigSection],
    primary_data: dict[str, Any] | None,
    last_good_data: dict[str, Any] | None,
    fallback_data: dict[str, Any],
) -> _ConfigSection:
    type_hints = _SECTION_FIELD_TYPES[section_name]
    values: dict[str, object] = {}

    for field_name, expected_type in type_hints.items():
        values[field_name] = _load_field(
            section_name,
            field_name,
            expected_type,
            primary_data,
            last_good_data,
            fallback_data,
        )
    return config_type(**values)


def _load_field(
    section_name: str,
    field_name: str,
    expected_type: object,
    primary_data: dict[str, Any] | None,
    last_good_data: dict[str, Any] | None,
    fallback_data: dict[str, Any],
) -> object:
    for data in (primary_data, last_good_data, fallback_data):
        value = _read_field(data, section_name, field_name, expected_type)
        if value is not None:
            return value
    raise ConfigError(f"No valid value for {section_name}.{field_name}")


def _read_field(
    data: dict[str, Any] | None,
    section_name: str,
    field_name: str,
    expected_type: object,
) -> object | None:
    if data is None:
        return None
    section = data.get(section_name)
    if not isinstance(section, dict):
        return None
    values = cast(dict[str, Any], section)
    value = values.get(field_name)
    if not _matches_type(value, expected_type):
        return None
    return value


# File and schema validation
def _try_read_toml(path: str | Path) -> dict[str, Any] | None:
    try:
        with Path(path).open("rb") as file:
            return tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _read_required_toml(path: str | Path) -> dict[str, Any]:
    try:
        with Path(path).open("rb") as file:
            return tomllib.load(file)
    except OSError as error:
        raise ConfigFileError(f"Cannot read fallback config {path}: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigFormatError(
            f"Invalid fallback TOML in config file {path}: {error}"
        ) from error


def _is_complete_valid_config(data: dict[str, Any] | None) -> bool:
    if data is None:
        return False
    try:
        _validate_complete_config(data)
    except ConfigError:
        return False
    return True


def _validate_complete_config(data: dict[str, Any]) -> None:
    _validate_keys(data, set(_SECTION_TYPES), "config")
    for section_name, config_type in _SECTION_TYPES.items():
        section = data[section_name]
        if not isinstance(section, dict):
            raise ConfigSchemaError(f"Missing or invalid section [{section_name}]")
        section_values = cast(dict[str, Any], section)
        field_names = set(_SECTION_FIELD_TYPES[section_name])
        _validate_keys(section_values, field_names, f"section [{section_name}]")
        _create_section(section_name, config_type, section_values)


def _validate_keys(
    values: dict[str, Any],
    expected_names: set[str],
    description: str,
) -> None:
    actual_names = set(values)
    if actual_names == expected_names:
        return
    missing = sorted(expected_names - actual_names)
    unexpected = sorted(actual_names - expected_names)
    raise ConfigSchemaError(
        f"Invalid {description} keys: missing={missing}, unexpected={unexpected}"
    )


def _create_section(
    section_name: str,
    config_type: type[_ConfigSection],
    values: dict[str, Any],
) -> _ConfigSection:
    try:
        return config_type(**values)
    except TypeError as error:
        raise ConfigSchemaError(
            f"Invalid keys in config section [{section_name}]: {error}"
        ) from error


# Last-known-good persistence
def _save_last_good(primary_path: str | Path, last_good_path: str | Path) -> None:
    source = Path(primary_path)
    destination = Path(last_good_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = destination.with_suffix(f"{destination.suffix}.tmp")
    shutil.copyfile(source, temporary_path)
    temporary_path.replace(destination)


Config = AgentConfig()


__all__ = [
    "AgentConfig",
    "ClassifierConfig",
    "ConfigError",
    "ConfigFileError",
    "ConfigFormatError",
    "ConfigSchemaError",
    "ConfigTypeError",
    "ProcessGuardConfig",
    "ScreenLockConfig",
    "ScreenMonitorConfig",
    "SystemConfig",
    "WebBlockerConfig",
    "WindowMonitorConfig",
    "Config",
]
