import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


class ConfigError(Exception):
    """Lỗi gốc của hệ thống config."""


class ConfigFileError(ConfigError):
    """Không thể đọc file config."""


class ConfigFormatError(ConfigError):
    """Nội dung TOML không hợp lệ."""


class ConfigSchemaError(ConfigError):
    """Section hoặc key config không khớp schema."""


class ConfigTypeError(ConfigError):
    """Giá trị config không đúng type hoặc không hợp lệ."""


@dataclass(frozen=True)
class Webblocker:
    block_game: bool
    block_gore: bool
    block_porn: bool
    block_social: bool

    # Ham dat biet cua dataclass
    def __post_init__(self):
        for var, val in vars(self).items():
            if not isinstance(val, bool):
                raise ConfigTypeError(
                    f"webblocker.{var} must contain True or False, not {val!r}"
                )


class ConfigObject:
    __slots__ = ("webblocker",)

    def __init__(self) -> None:
        object.__setattr__(
            self,
            "webblocker",
            Webblocker(
                True,
                True,
                True,
                True,
            ),
        )

    def __setattr__(self, name: str, value: object, /) -> None:
        raise ConfigError("Use ConfigObject.load() to update config")

    def load(self, path: str | Path) -> None:
        data = _read_toml(path)
        new_values: dict[str, object] = {}

        for attr_name in self.__slots__:
            section = _read_section(data, attr_name)
            current_value = getattr(self, attr_name)
            config_type = cast(type[Webblocker], type(current_value))
            try:
                new_values[attr_name] = config_type(**section)
            except TypeError as error:
                raise ConfigSchemaError(
                    f"Invalid keys in config section [{attr_name}]: {error}"
                ) from error

        for attr_name, value in new_values.items():
            object.__setattr__(self, attr_name, value)


def _read_toml(path: str | Path) -> dict[str, Any]:
    try:
        with Path(path).open("rb") as file:
            return tomllib.load(file)
    except OSError as error:
        raise ConfigFileError(f"Cannot read config file {path}: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigFormatError(f"Invalid TOML in config file {path}: {error}") from error


def _read_section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise ConfigSchemaError(f"Missing or invalid config section [{name}]")
    return cast(dict[str, Any], value)


if __name__ == "__main__":
    config_path = Path(__file__).resolve().parent / "sag_agent_config.toml"
    Config = ConfigObject()
    Config.load(config_path)
    print(Config.webblocker.block_porn)
