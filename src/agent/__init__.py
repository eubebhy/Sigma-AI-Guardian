"""Runtime cục bộ của SAG Agent.

File path: `src/agent/__init__.py`.
Input: caller tạo runtime qua `create_runtime()`.
Output: `AgentRuntime` quản lý adapter platform của một Agent process.
Nguyên lý: package này là điểm sở hữu duy nhất của chọn platform và lifecycle;
feature không import backend Linux hoặc Windows trực tiếp.
"""

from agent.runtime import AgentRuntime, create_runtime

__all__ = ["AgentRuntime", "create_runtime"]
