"""Factory và adapter nền tảng của SAG Agent.

File path: `src/agent/platform/__init__.py`.
Input: tên platform do runtime phát hiện hoặc truyền vào test.
Output: `PlatformServices` chứa adapter đúng một hệ điều hành.
Nguyên lý: import adapter được thực hiện lazy trong factory để dependency của OS kia
không ảnh hưởng lúc Agent khởi động.
"""

from agent.platform.factory import (
    PlatformServices,
    create_platform_services,
    get_default_platform_services,
)

__all__ = [
    "PlatformServices",
    "create_platform_services",
    "get_default_platform_services",
]
