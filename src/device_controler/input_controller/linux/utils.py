"""Compatibility API cho lifecycle Linux input controller."""

from agent.platform.linux.input_controller.utils import (
    UInputManager,
    create_ui,
    ui_alive,
)

__all__ = ["UInputManager", "create_ui", "ui_alive"]
