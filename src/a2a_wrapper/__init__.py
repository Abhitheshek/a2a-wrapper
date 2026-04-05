from __future__ import annotations

from importlib import import_module
from typing import Any


__version__ = "0.2.0"

_CLIENT_EXPORTS = {
    "A2AAgentClient",
    "A2AWrapperClientError",
    "A2AWrapperConfigurationError",
    "A2AWrapperRequestError",
    "AgentClient",
    "AgentInfo",
    "AgentResponse",
    "AgentResult",
    "Conversation",
    "StreamEvent",
}

_SERVER_EXPORTS = {
    "A2AExecutorBase",
    "A2ARequest",
    "A2AServerLauncher",
    "AgentCapability",
    "AgentHandlerBase",
    "AgentProfile",
    "AgentRequest",
    "AgentServer",
    "AgentServerConfig",
    "AgentSkillCard",
    "ExecutionHooks",
    "FunctionExecutor",
    "FunctionHandler",
    "ResponseContext",
    "TaskResponder",
    "create_agent_server",
    "create_server",
}

__all__ = sorted(_CLIENT_EXPORTS | _SERVER_EXPORTS | {"__version__"})


def __getattr__(name: str) -> Any:
    if name in _CLIENT_EXPORTS:
        module = import_module("a2a_wrapper._client")
        return getattr(module, name)
    if name in _SERVER_EXPORTS:
        module = import_module("a2a_wrapper._server")
        return getattr(module, name)
    raise AttributeError(f"module 'a2a_wrapper' has no attribute {name!r}")
