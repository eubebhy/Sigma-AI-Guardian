"""Compatibility API cho Linux keyboard sender."""

from device_controller.input_controller.linux import (
    keyDown,
    keyUp,
    press,
    supportedKeys,
    supportedWriteCharacters,
    write,
)

__all__ = [
    "keyDown",
    "keyUp",
    "press",
    "supportedKeys",
    "supportedWriteCharacters",
    "write",
]
