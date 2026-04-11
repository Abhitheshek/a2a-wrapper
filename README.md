# a2a-wrapper

`a2a-wrapper` is a small Python package for two common jobs:

1. expose your own agent logic as an A2A server
2. call A2A agents from Python with a simpler client API

It sits on top of the official Python `a2a-sdk`, but removes the repetitive wiring around request parsing, task updates, agent cards, and client result normalization.

## Who this is for

Use this package when you already have agent logic in your app and you want to:

- publish it as an A2A-compatible service
- connect to other A2A agents from Python
- keep your server and client code small and readable

If you want direct control over every SDK primitive, use `a2a-sdk` directly. If you want a cleaner application-facing layer, use `a2a-wrapper`.

## Install

Install from PyPI:

```bash
pip install a2a-wrapper
```

Framework extras:

```bash
pip install "a2a-wrapper[langchain]"
pip install "a2a-wrapper[crewai]"
```

If you are contributing to this repository itself:

```bash
pip install -e .
pip install -e .[dev]
```

Production users usually do not need editable installs. `-e` is only for local package development, where you want code changes in the repo to reflect immediately without reinstalling the package.

## Public API

Most projects will use these names:

```python
from a2a_wrapper import (
    AgentClient,
    AgentServer,
)
```

For advanced usage, typed helper classes are also available:

- `AgentCapability`
- `AgentRequest`
- `AgentResult`
- `AgentServerConfig`
- `Conversation`
- `ResponseContext`
- `StreamEvent`
- `ExecutionHooks`
- `create_agent_server`

The package also keeps backward-compatible aliases for older names such as `A2AAgentClient`, `A2AServerLauncher`, and `create_server`.

## API Reference

### Server-side classes

### `AgentCapability`

Represents one capability or skill that your server exposes in its A2A agent card.

Use it to describe:

- what the agent can do
- human-friendly capability name
- description
- tags
- example prompts

Typical use:

```python
AgentCapability(
    capability_id="summarize",
    name="Summarize",
    description="Summarizes long text",
    tags=["text", "summary"],
    examples=["Summarize this report"],
)
```

### `AgentServerConfig`

Holds the configuration for your server.

It controls:

- server name
- description
- version
- host
- port
- streaming support
- docs URL
- default input and output modes

This is the metadata and network configuration for your A2A server.

### `AgentRequest`

The normalized request object passed into your handler.

Main fields:

- `user_text`: extracted text from the incoming A2A message
- `task_id`: current A2A task id
- `context_id`: conversation or task context id
- `message_id`: underlying message id when available
- `raw_context`: original SDK request context
- `raw_message`: original SDK message object
- `metadata`: lightweight derived metadata

In most handlers, `request.user_text` is the main thing you need.

### `ResponseContext`

The object used by your handler to send task updates back to the client.

Main methods:

- `progress(text)`: send a working/progress update
- `working(text)`: same idea as progress, explicit working state
- `submit(text)`: mark task as accepted/submitted
- `complete(text)`: finish successfully with text output
- `complete_json(payload)`: finish with a JSON-like payload converted to text
- `add_text_artifact(text)`: attach intermediate text artifact
- `add_parts(parts)`: attach custom artifact parts
- `need_input(question)`: ask the caller for more input and end the current step
- `require_input(question)`: alias of `need_input`
- `require_auth(message)`: indicate authentication is required
- `reject(reason)`: reject the request
- `cancel(reason)`: cancel the task
- `failed(reason)`: mark the task as failed

This is the main class that maps your app logic to the A2A task lifecycle.

### `ExecutionHooks`

Optional lifecycle hooks for server execution.

Available hooks:

- `on_request`
- `on_success`
- `on_error`

Use this when you want cross-cutting behavior like:

- request logging
- metrics
- audit events
- centralized error reporting

### `AgentHandlerBase`

Base class for class-based server handlers.

Use it when you prefer a class-based execution model instead of a plain function handler. You implement `run(...)`, and the wrapper takes care of the surrounding request execution flow.

### `FunctionHandler`

Internal adapter that turns a normal Python function into an `AgentHandlerBase`.

Most users do not need to instantiate this directly because `create_agent_server(...)` and `AgentServer.from_handler(...)` handle it for you.

### `AgentServer`

The main server class.

What it does:

- building the agent card
- building the request handler
- creating the ASGI application
- running the server with `uvicorn`

Common methods:

- `capability()`
- `build_agent_card()`
- `build_request_handler()`
- `build_application()`
- `get_asgi_app()`
- `run()`

You can now create a server directly with `AgentServer(...)` using plain constructor arguments, and capability dictionaries are accepted for the common case.

Autofill behavior:

- if `capabilities` is omitted, a default capability is created from the server name and description
- if a capability mapping is missing `name` or `description`, those values are filled from the server
- if a capability mapping is missing `id`, it is generated from the server name

### `create_agent_server(...)`

Backward-compatible factory for creating an `AgentServer` from a normal handler function.

This still works, but `AgentServer(...)` is now the simplest entry point.

## Client-side classes

### `AgentClient`

The main Python client wrapper used to connect to an A2A agent.

It handles:

- connecting to the remote agent
- fetching the agent card
- sending blocking requests
- streaming responses
- task lookup and cancellation
- conversation tracking

Common methods:

- `connect()`
- `close()`
- `get_agent_info()`
- `send()`
- `ask()`
- `stream()`
- `ask_stream()`
- `get_task()`
- `cancel_task()`
- `new_conversation()`

### `AgentInfo`

Normalized agent card information returned by `get_agent_info()`.

It contains:

- `name`
- `description`
- `version`
- `url`
- `streaming`
- `skills`

Use this when you want to inspect what a remote A2A agent exposes.

### `AgentResult`

Normalized final result returned by blocking send operations.

It contains:

- `task_id`
- `context_id`
- `state`
- `text`
- `raw`

Convenience properties:

- `is_complete`
- `needs_input`
- `is_failed`
- `is_canceled`

### `StreamEvent`

Normalized event returned during streaming operations.

It contains:

- `task_id`
- `context_id`
- `state`
- `text`
- `raw`
- `is_final`

Use this when you want incremental updates while the remote agent is working.

### `Conversation`

Small helper object for multi-turn conversations.

It stores:

- `task_id`
- `context_id`

Pass it into `client.send(...)` or `client.stream(...)` to keep multiple requests in the same logical A2A context.

## Exceptions

### `A2AWrapperClientError`

Base exception for client-side wrapper errors.

### `A2AWrapperConfigurationError`

Raised when the client is configured with invalid values, such as an empty URL or invalid timeout.

### `A2AWrapperRequestError`

Raised when connecting, sending, streaming, fetching task data, or canceling a task fails.

## Backward-compatible aliases

These names exist for compatibility with older code:

- `A2AAgentClient` -> `AgentClient`
- `AgentResponse` -> `AgentResult`
- `A2AServerLauncher` -> `AgentServer`
- `A2ARequest` -> `AgentRequest`
- `AgentProfile` -> `AgentServerConfig`
- `AgentSkillCard` -> `AgentCapability`
- `TaskResponder` -> `ResponseContext`
- `FunctionExecutor` -> `FunctionHandler`
- `A2AExecutorBase` -> `AgentHandlerBase`
- `create_server` -> `create_agent_server`

## Quick Start: Build an A2A server

```python
from a2a_wrapper import AgentServer, AgentRequest, ResponseContext


async def handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.complete(f"Echo: {request.user_text}")


server = AgentServer(
    name="Echo Agent",
    description="Simple echo agent",
    host="0.0.0.0",
    port=10002,
    handler=handler,
)


if __name__ == "__main__":
    server.run()
```

What the wrapper gives your handler:

- `request.user_text` for normalized input text
- `request.task_id` and `request.context_id` for task context
- `responder.progress(...)`, `responder.complete(...)`, `responder.failed(...)`, and other lifecycle helpers

If you want stronger typing or more explicit construction, the older `AgentServerConfig`, `AgentCapability`, and `create_agent_server(...)` flow still works.

If you want to override the default capability:

```python
server = AgentServer(
    name="Research Agent",
    description="Runs research workflows",
    capabilities=[
        {
            "id": "research",
            "tags": ["research", "analysis"],
        }
    ],
    handler=handler,
)
```

In this example, `name` and `description` for the capability are filled automatically from the server.

## Quick Start: Call an A2A server

```python
import asyncio

from a2a_wrapper import AgentClient


async def main() -> None:
    async with AgentClient("http://localhost:10002") as client:
        info = await client.get_agent_info()
        print(info.name, info.skills)

        reply = await client.send("Hello")
        print(reply.state)
        print(reply.text)


asyncio.run(main())
```

## Core concepts

### `AgentServerConfig`

Defines your server identity and network settings:

- `name`
- `description`
- `version`
- `host`
- `port`
- `enable_streaming`
- `docs_url`

### `AgentCapability`

Describes a skill published in the A2A agent card:

```python
AgentCapability(
    capability_id="math_reasoning",
    name="Math Reasoning",
    description="Solves math and text-analysis requests",
    tags=["math", "tools"],
    examples=["What is 27 * 3 + 4?", "Count the words in this sentence"],
)
```

### `AgentRequest`

The normalized request object your handler receives. The field you will use most often is:

```python
request.user_text
```

### `ResponseContext`

The helper object your handler uses to update the task state. Common methods:

- `await responder.progress(text)`
- `await responder.complete(text)`
- `await responder.need_input(question)`
- `await responder.require_auth(message)`
- `await responder.reject(reason)`
- `await responder.cancel(reason)`
- `await responder.failed(reason)`

### `AgentClient`

The Python client wrapper. Common methods:

- `await client.get_agent_info()`
- `await client.send(text)`
- `await client.ask(text)`
- `await client.stream(text)`
- `await client.get_task(task_id)`
- `await client.cancel_task(task_id)`

Sync helpers are also available for scripts:

- `client.ask_sync(...)`
- `client.send_sync(...)`
- `client.get_agent_info_sync()`

## Multi-turn conversations

Use a `Conversation` when you want multiple messages to stay in the same logical task context:

```python
import asyncio

from a2a_wrapper import AgentClient


async def main() -> None:
    async with AgentClient("http://localhost:10002") as client:
        conversation = client.new_conversation()

        first = await client.send("Hello", conversation=conversation)
        second = await client.send(
            "Continue from the previous reply",
            conversation=conversation,
        )

        print(first.text)
        print(second.text)


asyncio.run(main())
```

## Blocking and streaming

Blocking request:

```python
reply = await client.send("Hello")
print(reply.text)
```

Streaming request:

```python
async for event in client.stream("Hello"):
    if event.text:
        print(event.text)
    if event.is_final:
        break
```

## Framework examples

This repository includes ready-to-run examples:

- `examples/my_langchain_agent.py`
- `examples/my_crewai_agent.py`

They show how to plug LangChain and CrewAI logic into the wrapper without rewriting A2A plumbing each time.

## Testing

Run the test suite:

```bash
pytest
```

Current coverage includes:

- public package exports
- client helper normalization
- missing-SDK import guard behavior
- an optional smoke test against a live local A2A server

## Practical notes

- Distribution name: `a2a-wrapper`
- Import name: `a2a_wrapper`
- Python requirement: `>=3.11`
- Console script: `a2a-wrapper-client`

## Documentation

See `DOCS.md` for:

- a real project integration guide
- server and client usage patterns
- LangChain and CrewAI examples
- task lifecycle methods
- recommended project structure
