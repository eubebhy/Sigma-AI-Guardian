"""Compatibility API cho Linux mouse sender."""

from device_controller.input_controller.linux import (
    click,
    mouseDown,
    mouseUp,
    moveRel,
    moveTo,
    position,
    scroll,
    sideScroll,
)

__all__ = [
    "click",
    "mouseDown",
    "mouseUp",
    "moveRel",
    "moveTo",
    "position",
    "scroll",
    "sideScroll",
]
