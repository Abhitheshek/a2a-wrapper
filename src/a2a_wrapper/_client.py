from __future__ import annotations

import argparse
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Iterable, List, Optional, Tuple

import httpx

try:
    from a2a.client import ClientConfig, ClientFactory, create_text_message_object
    from a2a.types import MessageSendConfiguration, TaskIdParams, TaskQueryParams
except ImportError as exc:  # pragma: no cover
    ClientConfig = None  # type: ignore[assignment]
    ClientFactory = None  # type: ignore[assignment]
    create_text_message_object = None  # type: ignore[assignment]
    MessageSendConfiguration = None  # type: ignore[assignment]
    TaskIdParams = None  # type: ignore[assignment]
    TaskQueryParams = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("a2a_wrapper.client")


class A2AWrapperClientError(RuntimeError):
    """Base exception for client wrapper failures."""


class A2AWrapperConfigurationError(A2AWrapperClientError):
    """Raised when the client is configured with invalid values."""


class A2AWrapperRequestError(A2AWrapperClientError):
    """Raised when an A2A request fails or returns invalid data."""


def _require_sdk() -> None:
    if _IMPORT_ERROR is not None:
        raise RuntimeError(
            "a2a-sdk is required for this wrapper. Install it with: pip install a2a-sdk"
        ) from _IMPORT_ERROR


def _safe_get(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
        if isinstance(obj, dict) and name in obj:
            return obj[name]
    return default


def _extract_text_from_parts(parts: Optional[Iterable[Any]]) -> str:
    chunks: List[str] = []
    for part in parts or []:
        root = _safe_get(part, "root")
        text = _safe_get(part, "text")
        if text:
            chunks.append(str(text))
            continue
        if root is not None:
            root_text = _safe_get(root, "text")
            if root_text:
                chunks.append(str(root_text))
    return "\n".join(chunk.strip() for chunk in chunks if chunk and chunk.strip())


def _extract_text_from_message(message: Any) -> str:
    return _extract_text_from_parts(_safe_get(message, "parts", default=[]))


def _extract_text_from_task(task: Any) -> str:
    status = _safe_get(task, "status", default=None)
    message = _safe_get(status, "message", default=None)
    text = _extract_text_from_message(message)
    if text:
        return text

    for artifact in _safe_get(task, "artifacts", default=[]) or []:
        artifact_text = _extract_text_from_parts(_safe_get(artifact, "parts", default=[]))
        if artifact_text:
            return artifact_text
    return ""


def _task_state(task: Any) -> str:
    status = _safe_get(task, "status", default=None)
    state = _safe_get(status, "state", default="unknown")
    return str(state)


def _task_ids(task: Any) -> Tuple[str, str]:
    return (
        str(_safe_get(task, "id", default="") or ""),
        str(_safe_get(task, "context_id", "contextId", default="") or ""),
    )


@dataclass(slots=True)
class AgentInfo:
    """Normalized agent card information returned by the client wrapper."""

    name: str
    description: str
    version: str
    url: str
    streaming: bool
    skills: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"AgentInfo(name={self.name!r}, version={self.version!r}, "
            f"url={self.url!r}, streaming={self.streaming}, skills={self.skills})"
        )


@dataclass(slots=True)
class Conversation:
    """Reusable task/context wrapper for multi-turn interactions."""

    task_id: Optional[str] = None
    context_id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass(slots=True)
class AgentResult:
    """Normalized result returned from a blocking A2A send operation."""

    task_id: str
    context_id: str
    state: str
    text: str
    raw: Any

    @property
    def is_complete(self) -> bool:
        return self.state == "completed"

    @property
    def needs_input(self) -> bool:
        return self.state == "input-required"

    @property
    def is_failed(self) -> bool:
        return self.state == "failed"

    @property
    def is_canceled(self) -> bool:
        return self.state == "canceled"


@dataclass(slots=True)
class StreamEvent:
    """Normalized event returned from a streaming A2A send operation."""

    task_id: str
    context_id: str
    state: str
    text: str
    raw: Any
    is_final: bool


class AgentClient:
    """Friendly client wrapper built on top of the official A2A Python SDK."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 120.0,
        prefer_streaming: bool = True,
        accepted_output_modes: Optional[List[str]] = None,
        agent_card_path: str = "/.well-known/agent.json",
    ):
        _require_sdk()
        if not base_url.strip():
            raise A2AWrapperConfigurationError("base_url must not be empty.")
        if timeout <= 0:
            raise A2AWrapperConfigurationError("timeout must be greater than 0.")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.prefer_streaming = prefer_streaming
        self.accepted_output_modes = accepted_output_modes or ["text/plain"]
        self.agent_card_path = agent_card_path
        self._httpx_client: Optional[httpx.AsyncClient] = None
        self._client: Any = None

    async def __aenter__(self) -> "AgentClient":
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def connect(self) -> "AgentClient":
        if self._client is not None:
            return self

        logger.info(
            "Connecting A2A client | url=%s card_path=%s prefer_streaming=%s",
            self.base_url,
            self.agent_card_path,
            self.prefer_streaming,
        )
        self._httpx_client = httpx.AsyncClient(timeout=self.timeout)
        config = ClientConfig(
            streaming=self.prefer_streaming,
            polling=True,
            httpx_client=self._httpx_client,
            accepted_output_modes=self.accepted_output_modes,
        )
        try:
            self._client = await ClientFactory.connect(
                self.base_url,
                client_config=config,
                relative_card_path=self.agent_card_path,
            )
        except Exception as exc:
            raise A2AWrapperRequestError(
                f"Failed to connect to A2A agent at {self.base_url}: {exc}"
            ) from exc
        return self

    async def close(self) -> None:
        if self._client is not None and hasattr(self._client, "close"):
            await self._client.close()
        self._client = None
        if self._httpx_client is not None:
            await self._httpx_client.aclose()
            self._httpx_client = None

    def new_conversation(self, *, context_id: Optional[str] = None) -> Conversation:
        return Conversation(context_id=context_id or uuid.uuid4().hex)

    async def _ensure_client(self) -> Any:
        if self._client is None:
            await self.connect()
        return self._client

    def _build_message(self, text: str, conversation: Optional[Conversation]) -> Any:
        if not text.strip():
            raise A2AWrapperConfigurationError("text must not be empty.")
        message = create_text_message_object(content=text)
        if conversation is not None:
            setattr(message, "context_id", conversation.context_id)
            if conversation.task_id:
                setattr(message, "task_id", conversation.task_id)
        return message

    def _build_config(self, *, blocking: bool, history_length: Optional[int] = None) -> Any:
        return MessageSendConfiguration(
            blocking=blocking,
            accepted_output_modes=self.accepted_output_modes,
            history_length=history_length,
        )

    def _event_to_result(self, event: Any) -> AgentResult:
        if isinstance(event, tuple):
            task, _update = event
            task_id, context_id = _task_ids(task)
            return AgentResult(
                task_id=task_id,
                context_id=context_id,
                state=_task_state(task),
                text=_extract_text_from_task(task) or "(empty response)",
                raw=event,
            )

        message = event
        task_id = str(_safe_get(message, "task_id", default="") or "")
        context_id = str(_safe_get(message, "context_id", "contextId", default="") or "")
        return AgentResult(
            task_id=task_id,
            context_id=context_id,
            state="completed",
            text=_extract_text_from_message(message) or "(empty response)",
            raw=event,
        )

    def _event_to_stream_event(self, event: Any) -> StreamEvent:
        result = self._event_to_result(event)
        return StreamEvent(
            task_id=result.task_id,
            context_id=result.context_id,
            state=result.state,
            text=result.text,
            raw=result.raw,
            is_final=result.state in {"completed", "failed", "input-required", "canceled"},
        )

    async def get_agent_info(self) -> AgentInfo:
        client = await self._ensure_client()
        try:
            card = await client.get_card()
        except Exception as exc:
            raise A2AWrapperRequestError(
                f"Failed to fetch agent card from {self.base_url}: {exc}"
            ) from exc

        capabilities = _safe_get(card, "capabilities", default=None)
        skills = [str(_safe_get(skill, "name", default="?")) for skill in _safe_get(card, "skills", default=[]) or []]
        return AgentInfo(
            name=str(_safe_get(card, "name", default="Unknown")),
            description=str(_safe_get(card, "description", default="")),
            version=str(_safe_get(card, "version", default="?")),
            url=str(_safe_get(card, "url", default=self.base_url)),
            streaming=bool(_safe_get(capabilities, "streaming", default=False)),
            skills=skills,
        )

    async def send(
        self,
        text: str,
        *,
        conversation: Optional[Conversation] = None,
        history_length: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AgentResult:
        client = await self._ensure_client()
        message = self._build_message(text, conversation)
        final_event: Any = None
        logger.info("Sending blocking message | url=%s", self.base_url)
        try:
            async for event in client.send_message(
                message,
                configuration=self._build_config(blocking=True, history_length=history_length),
                request_metadata=metadata,
            ):
                final_event = event
                if conversation is not None and isinstance(event, tuple):
                    task, _update = event
                    task_id, _context_id = _task_ids(task)
                    if task_id and not conversation.task_id:
                        conversation.task_id = task_id
        except Exception as exc:
            raise A2AWrapperRequestError(
                f"Failed to send message to {self.base_url}: {exc}"
            ) from exc

        if final_event is None:
            raise A2AWrapperRequestError("Agent returned no response.")

        return self._event_to_result(final_event)

    async def ask(
        self,
        text: str,
        *,
        conversation: Optional[Conversation] = None,
        history_length: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        return (
            await self.send(
                text,
                conversation=conversation,
                history_length=history_length,
                metadata=metadata,
            )
        ).text

    async def stream(
        self,
        text: str,
        *,
        conversation: Optional[Conversation] = None,
        history_length: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AsyncIterator[StreamEvent]:
        client = await self._ensure_client()
        message = self._build_message(text, conversation)
        logger.info("Streaming message | url=%s", self.base_url)
        try:
            async for event in client.send_message(
                message,
                configuration=self._build_config(blocking=False, history_length=history_length),
                request_metadata=metadata,
            ):
                if conversation is not None and isinstance(event, tuple):
                    task, _update = event
                    task_id, _context_id = _task_ids(task)
                    if task_id and not conversation.task_id:
                        conversation.task_id = task_id
                yield self._event_to_stream_event(event)
        except Exception as exc:
            raise A2AWrapperRequestError(
                f"Failed to stream message from {self.base_url}: {exc}"
            ) from exc

    async def get_task(self, task_id: str, *, history_length: int = 20) -> Any:
        client = await self._ensure_client()
        try:
            return await client.get_task(
                TaskQueryParams(id=task_id, history_length=history_length)
            )
        except Exception as exc:
            raise A2AWrapperRequestError(f"Failed to fetch task {task_id}: {exc}") from exc

    async def cancel_task(self, task_id: str) -> Any:
        client = await self._ensure_client()
        try:
            return await client.cancel_task(TaskIdParams(id=task_id))
        except Exception as exc:
            raise A2AWrapperRequestError(f"Failed to cancel task {task_id}: {exc}") from exc

    async def ask_stream(
        self,
        text: str,
        *,
        conversation: Optional[Conversation] = None,
        history_length: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        chunks: List[str] = []
        async for event in self.stream(
            text,
            conversation=conversation,
            history_length=history_length,
            metadata=metadata,
        ):
            if event.text:
                chunks.append(event.text)
            if event.is_final:
                break
        return "\n".join(chunks)

    def ask_sync(self, text: str, *, conversation: Optional[Conversation] = None) -> str:
        return asyncio.run(self.ask(text, conversation=conversation))

    def send_sync(
        self,
        text: str,
        *,
        conversation: Optional[Conversation] = None,
        history_length: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AgentResult:
        return asyncio.run(
            self.send(
                text,
                conversation=conversation,
                history_length=history_length,
                metadata=metadata,
            )
        )

    def get_agent_info_sync(self) -> AgentInfo:
        return asyncio.run(self.get_agent_info())

    def get_task_sync(self, task_id: str, *, history_length: int = 20) -> Any:
        return asyncio.run(self.get_task(task_id, history_length=history_length))

    def cancel_task_sync(self, task_id: str) -> Any:
        return asyncio.run(self.cancel_task(task_id))


A2AAgentClient = AgentClient
AgentResponse = AgentResult


async def _demo(url: str, message: str, stream: bool) -> None:
    async with AgentClient(url) as client:
        info = await client.get_agent_info()
        print(f"Agent: {info.name} ({info.version})")
        print(f"URL: {info.url}")
        print(f"Streaming: {info.streaming}")
        print(f"Skills: {', '.join(info.skills) or '-'}")
        print()

        if stream:
            async for event in client.stream(message):
                if event.text:
                    print(event.text)
                if event.is_final:
                    break
            return

        reply = await client.send(message)
        print(f"State: {reply.state}")
        print(reply.text)


def main() -> None:
    parser = argparse.ArgumentParser(description="A2A SDK based client wrapper")
    parser.add_argument("--url", default="http://localhost:10002", help="A2A agent base URL")
    parser.add_argument("--msg", default="Hello", help="Message to send")
    parser.add_argument("--stream", action="store_true", help="Prefer streaming response")
    args = parser.parse_args()
    asyncio.run(_demo(args.url, args.msg, args.stream))
