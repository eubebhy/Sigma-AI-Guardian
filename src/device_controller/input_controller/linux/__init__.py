"""Compatibility facade cho Linux input controller.

Implementation native nằm tại `agent.platform.linux.input_controller`; facade giữ
một operation adapter để tham gia lifecycle process-wide.
"""

from agent.platform.linux.input_controller_operations import (
    LinuxInputControllerOperations,
)


_operations = LinuxInputControllerOperations()
click = _operations.click
keyDown = _operations.keyDown
keyUp = _operations.keyUp
moveRel = _operations.moveRel
moveTo = _operations.moveTo
mouseDown = _operations.mouseDown
mouseUp = _operations.mouseUp
position = _operations.position
press = _operations.press
scroll = _operations.scroll
sideScroll = _operations.sideScroll
supportedKeys = _operations.supportedKeys
supportedWriteCharacters = _operations.supportedWriteCharacters
write = _operations.write

__all__ = [
    "click",
    "keyDown",
    "keyUp",
    "mouseDown",
    "mouseUp",
    "moveRel",
    "moveTo",
    "position",
    "press",
    "scroll",
    "sideScroll",
    "supportedKeys",
    "supportedWriteCharacters",
    "write",
]
