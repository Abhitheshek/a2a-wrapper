from __future__ import annotations

import inspect
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Sequence, Union

try:
    import uvicorn
    from a2a.server.agent_execution import AgentExecutor, RequestContext
    from a2a.server.apps import A2AStarletteApplication
    from a2a.server.events import EventQueue
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
    from a2a.types import AgentCapabilities, AgentCard, AgentSkill, TaskState
    from a2a.utils import new_agent_text_message
except ImportError as exc:  # pragma: no cover
    uvicorn = None  # type: ignore[assignment]
    AgentExecutor = object  # type: ignore[assignment]
    RequestContext = Any  # type: ignore[assignment]
    A2AStarletteApplication = Any  # type: ignore[assignment]
    EventQueue = Any  # type: ignore[assignment]
    DefaultRequestHandler = Any  # type: ignore[assignment]
    InMemoryTaskStore = Any  # type: ignore[assignment]
    TaskUpdater = Any  # type: ignore[assignment]
    AgentCapabilities = Any  # type: ignore[assignment]
    AgentCard = Any  # type: ignore[assignment]
    AgentSkill = Any  # type: ignore[assignment]
    TaskState = Any  # type: ignore[assignment]
    new_agent_text_message = None  # type: ignore[assignment]
    _SERVER_IMPORT_ERROR = exc
else:
    _SERVER_IMPORT_ERROR = None


LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("a2a_wrapper.server")

MaybeAwaitable = Union[Awaitable[Any], Any]
RequestHandler = Callable[["AgentRequest", "ResponseContext"], MaybeAwaitable]
CapabilityLike = Union["AgentCapability", Mapping[str, Any]]


def _require_server_runtime() -> None:
    if _SERVER_IMPORT_ERROR is not None:
        raise RuntimeError(
            "Server runtime dependencies are required. Install them with: "
            "pip install 'a2a-sdk[http-server]' uvicorn"
        ) from _SERVER_IMPORT_ERROR


def _ensure_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty.")
    return cleaned


def _slugify(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
    parts = [part for part in cleaned.split("-") if part]
    return "-".join(parts) or "agent"


async def _resolve(value: MaybeAwaitable) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _extract_text_from_parts(parts: Sequence[Any]) -> str:
    texts: List[str] = []
    for part in parts:
        if hasattr(part, "root") and hasattr(part.root, "text"):
            texts.append(str(part.root.text))
            continue
        if hasattr(part, "text"):
            texts.append(str(part.text))
            continue
        if isinstance(part, dict):
            if isinstance(part.get("root"), dict) and part["root"].get("text"):
                texts.append(str(part["root"]["text"]))
            elif part.get("text"):
                texts.append(str(part["text"]))
    return "\n".join(text.strip() for text in texts if str(text).strip())


@dataclass(slots=True)
class AgentCapability:
    """User-facing capability entry published in the A2A agent card."""

    capability_id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    input_modes: List[str] = field(default_factory=lambda: ["text/plain"])
    output_modes: List[str] = field(default_factory=lambda: ["text/plain"])

    def __post_init__(self) -> None:
        self.capability_id = _ensure_non_empty(self.capability_id, "capability_id")
        self.name = _ensure_non_empty(self.name, "name")
        self.description = _ensure_non_empty(self.description, "description")
        self.tags = [tag.strip() for tag in self.tags if tag.strip()]
        self.examples = [example.strip() for example in self.examples if example.strip()]
        self.input_modes = self.input_modes or ["text/plain"]
        self.output_modes = self.output_modes or ["text/plain"]

    def to_sdk_type(self) -> AgentSkill:
        return AgentSkill(
            id=self.capability_id,
            name=self.name,
            description=self.description,
            tags=self.tags,
            examples=self.examples or None,
            inputModes=self.input_modes,
            outputModes=self.output_modes,
        )


@dataclass(slots=True)
class AgentServerConfig:
    """Configuration for an A2A agent server."""

    name: str
    description: str
    version: str = "1.0.0"
    host: str = "127.0.0.1"
    port: int = 10002
    enable_streaming: bool = True
    docs_url: Optional[str] = None
    default_input_modes: List[str] = field(default_factory=lambda: ["text/plain"])
    default_output_modes: List[str] = field(default_factory=lambda: ["text/plain"])

    def __post_init__(self) -> None:
        self.name = _ensure_non_empty(self.name, "name")
        self.description = _ensure_non_empty(self.description, "description")
        self.version = _ensure_non_empty(self.version, "version")
        self.host = _ensure_non_empty(self.host, "host")
        if not (1 <= self.port <= 65535):
            raise ValueError("port must be between 1 and 65535.")

    @property
    def base_url(self) -> str:
        public_host = "localhost" if self.host == "0.0.0.0" else self.host
        return f"http://{public_host}:{self.port}/"

    def build_agent_card(self, skills: Sequence[AgentCapability]) -> AgentCard:
        _require_server_runtime()
        return AgentCard(
            name=self.name,
            description=self.description,
            url=self.base_url,
            version=self.version,
            documentationUrl=self.docs_url,
            defaultInputModes=self.default_input_modes,
            defaultOutputModes=self.default_output_modes,
            capabilities=AgentCapabilities(streaming=self.enable_streaming),
            skills=[skill.to_sdk_type() for skill in skills],
        )


@dataclass(slots=True)
class AgentRequest:
    """Normalized request object passed to your server handler."""

    user_text: str
    task_id: str
    context_id: str
    message_id: Optional[str]
    raw_context: RequestContext
    raw_message: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_context(cls, context: RequestContext) -> "AgentRequest":
        message = getattr(context, "message", None)
        parts = getattr(message, "parts", []) or []
        return cls(
            user_text=_extract_text_from_parts(parts),
            task_id=getattr(context, "task_id", ""),
            context_id=getattr(context, "context_id", ""),
            message_id=getattr(message, "message_id", None),
            raw_context=context,
            raw_message=message,
            metadata={"role": getattr(message, "role", None), "parts_count": len(parts)},
        )


class ResponseContext:
    """Friendly wrapper around the SDK TaskUpdater."""

    def __init__(self, task_updater: TaskUpdater):
        self._updater = task_updater
        self._closed = False

    @property
    def is_closed(self) -> bool:
        return self._closed

    async def _artifact(self, text: str, *, artifact_id: Optional[str] = None) -> None:
        await self._updater.add_artifact(
            parts=[{"kind": "text", "text": text}],
            artifact_id=artifact_id or str(uuid.uuid4()),
        )

    async def add_text_artifact(self, text: str, *, artifact_id: Optional[str] = None) -> None:
        await self._artifact(text, artifact_id=artifact_id)

    async def add_parts(self, parts: List[dict[str, Any]], *, artifact_id: Optional[str] = None) -> None:
        await self._updater.add_artifact(
            parts=parts,
            artifact_id=artifact_id or str(uuid.uuid4()),
        )

    async def complete(self, text: str) -> None:
        await self._artifact(text)
        await self._updater.complete()
        self._closed = True

    async def complete_json(self, payload: Dict[str, Any]) -> None:
        await self.complete(str(payload))

    async def working(self, text: str) -> None:
        await self._updater.start_work(message=new_agent_text_message(text))

    async def progress(self, text: str) -> None:
        await self.working(text)

    async def submit(self, text: str = "Task submitted.") -> None:
        await self._updater.submit(message=new_agent_text_message(text))

    async def need_input(self, question: str) -> None:
        await self._updater.requires_input(message=new_agent_text_message(question), final=True)
        self._closed = True

    async def require_input(self, question: str) -> None:
        await self.need_input(question)

    async def require_auth(self, message: str = "Authentication required.") -> None:
        await self._updater.requires_auth(message=new_agent_text_message(message), final=True)
        self._closed = True

    async def reject(self, reason: str) -> None:
        await self._updater.reject(message=new_agent_text_message(reason))
        self._closed = True

    async def cancel(self, reason: str = "Task cancelled.") -> None:
        await self._updater.cancel(message=new_agent_text_message(reason))
        self._closed = True

    async def failed(self, reason: str) -> None:
        await self._updater.failed(message=new_agent_text_message(f"Error: {reason}"))
        self._closed = True


@dataclass(slots=True)
class ExecutionHooks:
    on_request: Optional[Callable[[AgentRequest], MaybeAwaitable]] = None
    on_success: Optional[Callable[[AgentRequest], MaybeAwaitable]] = None
    on_error: Optional[Callable[[AgentRequest, Exception], MaybeAwaitable]] = None


class AgentHandlerBase(AgentExecutor):
    """Base class for writing custom A2A server handlers."""

    def __init__(self, hooks: Optional[ExecutionHooks] = None):
        _require_server_runtime()
        self._hooks = hooks or ExecutionHooks()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        responder = ResponseContext(updater)
        request = AgentRequest.from_context(context)
        logger.info(
            "Request received | task_id=%s context_id=%s text=%r",
            request.task_id,
            request.context_id,
            request.user_text,
        )
        try:
            if self._hooks.on_request:
                await _resolve(self._hooks.on_request(request))
            await self._invoke_run(request, responder)
            if not responder.is_closed:
                raise RuntimeError(
                    "Handler finished without sending a terminal response. "
                    "Call responder.complete(), responder.need_input(), or responder.failed()."
                )
            if self._hooks.on_success:
                await _resolve(self._hooks.on_success(request))
        except Exception as exc:
            logger.exception("Handler failure")
            if self._hooks.on_error:
                await _resolve(self._hooks.on_error(request, exc))
            if not responder.is_closed:
                await responder.failed(str(exc))

    async def _invoke_run(self, request: AgentRequest, responder: ResponseContext) -> None:
        signature = inspect.signature(self.run)
        parameter_names = list(signature.parameters)
        if parameter_names and parameter_names[0] in {"request", "agent_request"}:
            result = self.run(request, responder)
        else:
            result = self.run(request.user_text, responder)
        await _resolve(result)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.update_status(
            TaskState.canceled,
            message=new_agent_text_message("Task cancelled."),
            final=True,
        )

    async def run(
        self,
        request_or_text: Union[AgentRequest, str],
        responder: ResponseContext,
    ) -> None:
        raise NotImplementedError


class FunctionHandler(AgentHandlerBase):
    def __init__(self, handler: RequestHandler, hooks: Optional[ExecutionHooks] = None):
        super().__init__(hooks=hooks)
        self._handler = handler

    async def run(self, request: AgentRequest, responder: ResponseContext) -> None:
        result = await _resolve(self._handler(request, responder))
        if result is not None and not responder.is_closed:
            await responder.complete(str(result))


class AgentServer:
    """Friendly server builder for exposing custom agents over A2A.

    For the common case, you only need:

    - server name
    - server description
    - handler

    Capabilities are optional. If omitted, the server creates a default capability
    from the server name and description. If you pass capability mappings with
    missing fields, the server fills them from the server details.
    """

    def __init__(
        self,
        config: Optional[AgentServerConfig] = None,
        capabilities: Optional[Sequence[CapabilityLike]] = None,
        handler: Optional[Union[AgentExecutor, RequestHandler]] = None,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        version: str = "1.0.0",
        host: str = "127.0.0.1",
        port: int = 10002,
        enable_streaming: bool = True,
        docs_url: Optional[str] = None,
        default_input_modes: Optional[Sequence[str]] = None,
        default_output_modes: Optional[Sequence[str]] = None,
        hooks: Optional[ExecutionHooks] = None,
        task_store_factory: Optional[Callable[[], Any]] = None,
    ):
        _require_server_runtime()
        if config is None:
            if name is None or description is None:
                raise ValueError(
                    "Provide either config=AgentServerConfig(...) or both name= and description=."
                )
            config = AgentServerConfig(
                name=name,
                description=description,
                version=version,
                host=host,
                port=port,
                enable_streaming=enable_streaming,
                docs_url=docs_url,
                default_input_modes=list(default_input_modes or ["text/plain"]),
                default_output_modes=list(default_output_modes or ["text/plain"]),
            )
        if handler is None:
            raise ValueError("handler is required.")
        self.config = config
        normalized_capabilities = capabilities or [self._default_capability_mapping(config)]
        self.capabilities = [
            self._coerce_capability(
                capability,
                default_name=config.name,
                default_description=config.description,
            )
            for capability in normalized_capabilities
        ]
        self.handler = self._coerce_handler(handler, hooks=hooks)
        self.task_store_factory = task_store_factory or InMemoryTaskStore

    @staticmethod
    def capability(
        capability_id: str,
        name: str,
        description: str,
        *,
        tags: Optional[Sequence[str]] = None,
        examples: Optional[Sequence[str]] = None,
        input_modes: Optional[Sequence[str]] = None,
        output_modes: Optional[Sequence[str]] = None,
    ) -> AgentCapability:
        return AgentCapability(
            capability_id=capability_id,
            name=name,
            description=description,
            tags=list(tags or []),
            examples=list(examples or []),
            input_modes=list(input_modes or ["text/plain"]),
            output_modes=list(output_modes or ["text/plain"]),
        )

    @staticmethod
    def _default_capability_mapping(config: AgentServerConfig) -> dict[str, str]:
        return {
            "id": _slugify(config.name),
            "name": config.name,
            "description": config.description,
        }

    @staticmethod
    def _coerce_capability(
        capability: CapabilityLike,
        *,
        default_name: str,
        default_description: str,
    ) -> AgentCapability:
        if isinstance(capability, AgentCapability):
            return capability
        if not isinstance(capability, Mapping):
            raise TypeError("capabilities must contain AgentCapability objects or mapping values.")
        capability_id = capability.get("capability_id", capability.get("id")) or _slugify(default_name)
        name = capability.get("name") or default_name
        description = capability.get("description") or default_description
        return AgentCapability(
            capability_id=str(capability_id),
            name=str(name),
            description=str(description),
            tags=[str(tag) for tag in capability.get("tags", []) or []],
            examples=[str(example) for example in capability.get("examples", []) or []],
            input_modes=[str(mode) for mode in capability.get("input_modes", ["text/plain"]) or ["text/plain"]],
            output_modes=[str(mode) for mode in capability.get("output_modes", ["text/plain"]) or ["text/plain"]],
        )

    @staticmethod
    def _coerce_handler(
        handler: Union[AgentExecutor, RequestHandler],
        *,
        hooks: Optional[ExecutionHooks] = None,
    ) -> AgentExecutor:
        if isinstance(handler, AgentHandlerBase):
            return handler
        if hasattr(handler, "execute") and callable(getattr(handler, "execute")):
            return handler  # type: ignore[return-value]
        return FunctionHandler(handler=handler, hooks=hooks)  # type: ignore[arg-type]

    @classmethod
    def from_handler(
        cls,
        *,
        config: AgentServerConfig,
        capabilities: Sequence[AgentCapability],
        handler: RequestHandler,
        hooks: Optional[ExecutionHooks] = None,
        task_store_factory: Optional[Callable[[], Any]] = None,
    ) -> "AgentServer":
        return cls(
            config=config,
            capabilities=capabilities,
            handler=FunctionHandler(handler=handler, hooks=hooks),
            task_store_factory=task_store_factory,
        )

    def build_agent_card(self) -> AgentCard:
        return self.config.build_agent_card(self.capabilities)

    def build_request_handler(self) -> DefaultRequestHandler:
        _require_server_runtime()
        logger.info(
            "Building request handler | agent=%s capabilities=%s",
            self.config.name,
            [capability.capability_id for capability in self.capabilities],
        )
        return DefaultRequestHandler(
            agent_executor=self.handler,
            task_store=self.task_store_factory(),
        )

    def build_application(self) -> A2AStarletteApplication:
        _require_server_runtime()
        return A2AStarletteApplication(
            agent_card=self.build_agent_card(),
            http_handler=self.build_request_handler(),
        )

    def get_asgi_app(self):
        return self.build_application().build()

    def run(self, log_level: str = "info") -> None:
        _require_server_runtime()
        logger.info(
            "Starting A2A server | name=%s url=%s streaming=%s",
            self.config.name,
            self.config.base_url,
            self.config.enable_streaming,
        )
        uvicorn.run(
            self.get_asgi_app(),
            host=self.config.host,
            port=self.config.port,
            log_level=log_level,
        )


def create_agent_server(
    *,
    config: AgentServerConfig,
    capabilities: Sequence[AgentCapability],
    handler: RequestHandler,
    hooks: Optional[ExecutionHooks] = None,
    task_store_factory: Optional[Callable[[], Any]] = None,
) -> AgentServer:
    return AgentServer.from_handler(
        config=config,
        capabilities=capabilities,
        handler=handler,
        hooks=hooks,
        task_store_factory=task_store_factory,
    )


# Backward-compatible aliases
A2ARequest = AgentRequest
A2AExecutorBase = AgentHandlerBase
A2AServerLauncher = AgentServer
AgentProfile = AgentServerConfig
AgentSkillCard = AgentCapability
FunctionExecutor = FunctionHandler
TaskResponder = ResponseContext
create_server = create_agent_server
