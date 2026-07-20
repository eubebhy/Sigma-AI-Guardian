# pyright: reportPrivateUsage=false
"""CLI gọi tuần tự các API điều khiển keyboard và mouse Linux.

File path: `tests/input_controller/kb_mouse_control_cli.py`
Input: chuỗi flag thao tác; thứ tự flag chính là thứ tự thực thi.
Output: phát input thật qua Linux input controller và in thao tác đang chạy.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import TypeAlias, cast

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from utils.input_controller import linux
from utils.input_controller.linux import sendinput_kb, sendinput_mouse
from utils.input_controller.types import Keys, MouseButton

Command: TypeAlias = tuple[str, tuple[str, ...]]
_ARG_COUNTS = {
    "--key-down": 1,
    "--key-up": 1,
    "--press": 1,
    "--write": 1,
    "--mouse-down": 1,
    "--mouse-up": 1,
    "--click": 1,
    "--move-to": 2,
    "--move-rel": 2,
    "--scroll": 1,
    "--side-scroll": 1,
    "--position": 0,
    "--delay": 1,
    "--list-keys": 0,
}
_MOUSE_BUTTONS = {"left", "right", "middle", "forward", "back"}
_DEVICE_READY_DELAY = 0.67


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Linux keyboard/mouse actions in flag order.",
        epilog=(
            "Example: --move-to 500 300 --click left --write 'Hello' --press enter"
        ),
    )
    parser.add_argument("--key-down", metavar="KEY")
    parser.add_argument("--key-up", metavar="KEY")
    parser.add_argument("--press", metavar="KEY")
    parser.add_argument("--write", metavar="TEXT")
    parser.add_argument("--mouse-down", metavar="BUTTON")
    parser.add_argument("--mouse-up", metavar="BUTTON")
    parser.add_argument("--click", metavar="BUTTON")
    parser.add_argument("--move-to", nargs=2, metavar=("X", "Y"))
    parser.add_argument("--move-rel", nargs=2, metavar=("X", "Y"))
    parser.add_argument("--scroll", metavar="AMOUNT")
    parser.add_argument("--side-scroll", metavar="AMOUNT")
    parser.add_argument("--position", action="store_true")
    parser.add_argument("--delay", metavar="SECONDS")
    parser.add_argument("--list-keys", action="store_true")
    return parser


def _parse_commands(
    parser: argparse.ArgumentParser,
    arguments: list[str],
) -> list[Command]:
    commands: list[Command] = []
    index = 0
    while index < len(arguments):
        flag = arguments[index]
        count = _ARG_COUNTS.get(flag)
        if count is None:
            parser.error(f"unknown action: {flag}")
        values = tuple(arguments[index + 1 : index + 1 + count])
        if len(values) != count:
            parser.error(f"{flag} requires {count} value(s)")
        commands.append((flag, values))
        index += count + 1
    return commands


def _prepare_devices() -> None:
    """Tạo virtual devices và chờ Xorg/libinput attach trước action đầu tiên."""

    sendinput_kb._get_ui()
    sendinput_mouse._get_ui()
    time.sleep(_DEVICE_READY_DELAY)


def _execute(command: Command, parser: argparse.ArgumentParser) -> None:
    action, values = command
    print(action, *values, flush=True)

    if action == "--write":
        linux.write(values[0])

    elif action in {"--key-down", "--key-up", "--press"}:
        if values[0] not in linux.supportedKeys():
            parser.error(f"unsupported key: {values[0]}")

        key = cast(Keys, values[0])

        if action == "--key-down":
            linux.keyDown(key)

        elif action == "--key-up":
            linux.keyUp(key)

        else:
            linux.press(key)

    elif action in {"--mouse-down", "--mouse-up", "--click"}:
        if values[0] not in _MOUSE_BUTTONS:
            parser.error(f"unsupported mouse button: {values[0]}")

        button = cast(MouseButton, values[0])

        if action == "--mouse-down":
            linux.mouseDown(button)

        elif action == "--mouse-up":
            linux.mouseUp(button)

        else:
            linux.click(button)

    elif action == "--move-to":
        linux.moveTo(int(values[0]), int(values[1]))

    elif action == "--move-rel":
        linux.moveRel(int(values[0]), int(values[1]))

    elif action == "--scroll":
        linux.scroll(int(values[0]))

    elif action == "--side-scroll":
        linux.sideScroll(int(values[0]))

    elif action == "--position":
        print("position:", linux.position())

    elif action == "--delay":
        time.sleep(float(values[0]))

    elif action == "--list-keys":
        print("keys:", " ".join(linux.supportedKeys()))


def main() -> None:
    parser = _build_parser()
    arguments = sys.argv[1:]
    if not arguments:
        parser.print_help()
        return
    if arguments == ["--help"] or arguments == ["-h"]:
        parser.print_help()
        return
    commands = _parse_commands(parser, arguments)
    print(f"Preparing virtual devices for {_DEVICE_READY_DELAY:.2f}s", flush=True)
    _prepare_devices()
    for command in commands:
        _execute(command, parser)


if __name__ == "__main__":
    main()
