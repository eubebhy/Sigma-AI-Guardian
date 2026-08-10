"""Protocol lifecycle chung cho service và resource của SAG Agent.

File path: `src/agent/protocols.py`.
Input: object do runtime hoặc feature sở hữu.
Output: contract lifecycle chuẩn hóa qua `Service` và `Resource`.

Nguyên lý:
- `Service` chủ động vận hành nền và cần `start()`/`stop()`.
- `Resource` giữ tài nguyên cần giải phóng và cần `close()`.
- Một object có thể đồng thời là Service và Resource khi có cả hai trách nhiệm.
- Owner cấp cao gọi lifecycle; object tự dọn resource nội bộ của nó.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Service(Protocol):
    """Đối tượng vận hành chủ động, do AgentRuntime quyết định lúc start và stop.

    Ví dụ: worker nền hoặc vòng lặp poll. `stop()` phải yêu cầu service kết thúc,
    nhưng không thay thế `close()` khi service còn giữ resource cần giải phóng.
    """

    def start(self) -> None: ...

    def stop(self) -> None: ...


@runtime_checkable
class Resource(Protocol):
    """Đối tượng giữ resource cần được owner đóng khi không còn dùng.

    Ví dụ: classifier giữ local model; Linux input controller giữ UInput. `close()`
    phải an toàn khi resource chưa được tạo và khi được gọi lặp lại. Windows input
    controller không giữ resource vẫn triển khai `close()` no-op để giữ contract.
    """

    def close(self) -> None: ...


__all__ = ["Resource", "Service"]
