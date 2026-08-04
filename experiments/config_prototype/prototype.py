import tomllib
from pathlib import Path
from dataclasses import dataclass


@dataclass(frozen=True)
class Webblocker:
    block_game: bool
    block_gore: bool
    block_porn: bool
    block_social: bool

    # Ham dat biet cua decorator "dataclass"
    def __post_init__(self) -> None:
        for var, val in vars(self).items():
            if not isinstance(val, bool):
                raise RuntimeError(f'Webblocker "{var}" must be boolean')


def _read_toml(path: str | Path):
    with open(path, "rb") as f:
        return tomllib.load(f)


class ConfigObject:
    __slots__ = ["webblocker"]

    def __init__(self) -> None:
        object.__setattr__(self, "webblocker", Webblocker(True, True, True, True))

    def __setattr__(self, name: str, value: object, /) -> None:
        del name, value
        raise RuntimeError("You can ONLY change ConfigObject's value by reload config!")

    def load(self, path: str | Path) -> None:
        data = _read_toml(path)
        for obj_name in self.__slots__:
            cur_obj = getattr(self, obj_name)
            cur_class = type(cur_obj)

            object.__setattr__(self, obj_name, cur_class(**data[obj_name]))


if __name__ == "__main__":
    config_file_path = Path(__file__).resolve().parent / "config.toml"
    config = ConfigObject()
    config.load(path=config_file_path)
    print(config.webblocker.block_game)
