"""Public entry point của SAG Agent Runtime.

File path: `src/agent/runtime/__init__.py`.
Input: config và platform name tùy chọn.
Output: `AgentRuntime`, request/result types và factory `create_runtime()`.
Nguyên lý: package che giấu registry, manager và command routing phía sau Runtime.
"""

from agent.runtime.request_types import Request, Response
from agent.runtime.agent_runtime import AgentRuntime, create_runtime

__all__ = ["AgentRuntime", "Request", "Response", "create_runtime"]
