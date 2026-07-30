"""Compatibility API cho Windows keyboard sender."""

from device_controler.input_controller.window import (
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
