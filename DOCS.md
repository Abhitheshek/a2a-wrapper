# a2a-wrapper Guide

This guide is for developers who want to use `a2a-wrapper` in a real project.

The package solves two problems:

1. turning your own agent logic into an A2A server
2. calling A2A agents from Python without repeatedly handling low-level SDK shapes

The package is built on top of the official Python `a2a-sdk`. It does not replace the SDK. It gives you a friendlier application layer on top of it.

## 1. Package names

- PyPI package: `a2a-wrapper`
- Python import: `a2a_wrapper`

## 2. Install

Base install from PyPI:

```bash
pip install a2a-wrapper
```

Optional extras:

```bash
pip install "a2a-wrapper[langchain]"
pip install "a2a-wrapper[crewai]"
```

If you are developing this repository locally:

```bash
pip install -e .
pip install -e .[dev]
```

For normal package usage from PyPI, you do not need editable install mode.

## 3. Public API

Use these names for new code:

```python
from a2a_wrapper import (
    AgentClient,
    AgentServer,
)
```

For advanced usage, these helper types are also available:

- `AgentCapability`
- `AgentRequest`
- `AgentResult`
- `AgentServerConfig`
- `Conversation`
- `ResponseContext`
- `StreamEvent`
- `ExecutionHooks`
- `create_agent_server`

Backward-compatible aliases are also available:

- `A2AAgentClient`
- `A2AServerLauncher`
- `A2ARequest`
- `AgentProfile`
- `AgentSkillCard`
- `TaskResponder`
- `create_server`

## 4. API reference

This section explains the important classes and what they do in practice.

### `AgentCapability`

Server capability metadata.

Purpose:

- tells clients what your agent can do
- becomes part of the published A2A agent card

Important fields:

- `capability_id`
- `name`
- `description`
- `tags`
- `examples`
- `input_modes`
- `output_modes`

### `AgentServerConfig`

Server configuration and identity.

Purpose:

- defines how your server appears to clients
- controls host, port, version, and streaming metadata

Important fields:

- `name`
- `description`
- `version`
- `host`
- `port`
- `enable_streaming`
- `docs_url`
- `default_input_modes`
- `default_output_modes`

### `AgentRequest`

Normalized request object passed to your handler.

Purpose:

- gives your app one stable request shape
- hides low-level message-part extraction

Useful fields:

- `user_text`
- `task_id`
- `context_id`
- `message_id`
- `raw_context`
- `raw_message`
- `metadata`

### `ResponseContext`

Task lifecycle helper used inside server handlers.

Purpose:

- lets your handler update the current task
- provides readable methods for common A2A states

Main methods:

- `progress(...)`
- `working(...)`
- `submit(...)`
- `complete(...)`
- `complete_json(...)`
- `add_text_artifact(...)`
- `add_parts(...)`
- `need_input(...)`
- `require_input(...)`
- `require_auth(...)`
- `reject(...)`
- `cancel(...)`
- `failed(...)`

### `ExecutionHooks`

Optional hook container for:

- request logging
- metrics
- tracing
- centralized success/error side effects

Fields:

- `on_request`
- `on_success`
- `on_error`

### `AgentHandlerBase`

Base class for class-based server handlers.

Use this when:

- you want inheritance
- you want reusable handler classes
- you prefer `run(...)` methods over plain functions

### `FunctionHandler`

Adapter that wraps a normal function handler into the class-based server execution model.

Most users do not create this directly.

### `AgentServer`

Wrapper server object.

Purpose:

- owns config, capabilities, and handler
- builds the A2A application
- runs the HTTP server

Autofill behavior:

- if `capabilities` is omitted, the server creates one default capability
- default capability id is generated from the server name
- default capability name comes from the server name
- default capability description comes from the server description
- partial capability mappings inherit missing values from the server details

Useful methods:

- `capability()`
- `build_agent_card()`
- `build_request_handler()`
- `build_application()`
- `get_asgi_app()`
- `run()`

### `AgentClient`

Main client wrapper for talking to an A2A server.

Purpose:

- connect to a remote agent
- send messages
- stream updates
- inspect tasks
- cancel tasks

Useful methods:

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

Normalized agent card info returned by the client.

Fields:

- `name`
- `description`
- `version`
- `url`
- `streaming`
- `skills`

### `AgentResult`

Normalized final result for blocking requests.

Fields:

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

Normalized event for streaming requests.

Fields:

- `task_id`
- `context_id`
- `state`
- `text`
- `raw`
- `is_final`

### `Conversation`

Small helper for multi-turn continuity.

Fields:

- `task_id`
- `context_id`

### Exceptions

- `A2AWrapperClientError`: base client error
- `A2AWrapperConfigurationError`: invalid client configuration
- `A2AWrapperRequestError`: connection or request failure

## 5. How the server side works

When you build a server with `AgentServer(...)` or `create_agent_server(...)`, the wrapper handles:

- agent card creation
- request handler wiring
- request normalization
- task updater plumbing
- ASGI application creation
- `uvicorn` startup

Your code mainly focuses on:

- capability metadata
- business logic
- final responses

### Minimal server

```python
from a2a_wrapper import (
    AgentServer,
    AgentRequest,
    ResponseContext,
)


async def echo_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.progress("Processing request...")
    await responder.complete(f"Echo: {request.user_text}")


server = AgentServer(
    name="Echo Agent",
    description="Simple echo server",
    host="0.0.0.0",
    port=10002,
    handler=echo_handler,
)


if __name__ == "__main__":
    server.run()
```

In this form, the server auto-creates a default capability from:

- `name="Echo Agent"`
- `description="Simple echo server"`

### Minimal server with partial capability override

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
    handler=echo_handler,
)
```

In this case:

- capability id stays `research`
- capability name becomes `Research Agent`
- capability description becomes `Runs research workflows`

## 6. Server concepts

### `AgentServerConfig`

This controls your server identity and network settings.

```python
config = AgentServerConfig(
    name="Support Agent",
    description="Answers support questions",
    version="1.0.0",
    host="0.0.0.0",
    port=10002,
    enable_streaming=True,
    docs_url="https://your-docs.example.com",
)
```

Important fields:

- `name`
- `description`
- `version`
- `host`
- `port`
- `enable_streaming`
- `docs_url`
- `default_input_modes`
- `default_output_modes`

### `AgentCapability`

This is the skill metadata published in the A2A agent card.

```python
capability = AgentCapability(
    capability_id="summarize",
    name="Summarize",
    description="Summarizes long text into concise bullets",
    tags=["text", "summary"],
    examples=["Summarize this meeting transcript"],
)
```

### `AgentRequest`

This is the normalized input object passed to your handler.

Useful fields:

- `request.user_text`
- `request.task_id`
- `request.context_id`
- `request.message_id`
- `request.raw_context`
- `request.raw_message`
- `request.metadata`

Most handlers only need `request.user_text`.

### `ResponseContext`

This wraps the SDK task updater and gives you readable lifecycle methods.

Common methods:

- `await responder.progress(text)`
- `await responder.working(text)`
- `await responder.submit(text="Task submitted.")`
- `await responder.complete(text)`
- `await responder.complete_json(payload)`
- `await responder.add_text_artifact(text)`
- `await responder.add_parts(parts)`
- `await responder.need_input(question)`
- `await responder.require_input(question)`
- `await responder.require_auth(message)`
- `await responder.reject(reason)`
- `await responder.cancel(reason)`
- `await responder.failed(reason)`

## 7. Server response patterns

### Return a normal final answer

```python
async def handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.complete(f"Received: {request.user_text}")
```

### Send progress before finishing

```python
async def handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.submit("Task accepted.")
    await responder.progress("Working on your request...")
    await responder.complete("Done")
```

### Ask the client for more input

```python
async def handler(request: AgentRequest, responder: ResponseContext) -> None:
    if not request.user_text.strip():
        await responder.require_input("Please send a non-empty prompt.")
        return

    await responder.complete("Thanks")
```

### Fail explicitly

```python
async def handler(request: AgentRequest, responder: ResponseContext) -> None:
    try:
        result = do_work(request.user_text)
    except Exception as exc:
        await responder.failed(str(exc))
        return

    await responder.complete(result)
```

### Return artifacts

```python
async def handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.add_text_artifact("Intermediate report")
    await responder.complete("Final answer")
```

## 8. How the client side works

`AgentClient` wraps the official SDK client and normalizes different result shapes into a simpler interface.

The wrapper handles:

- SDK connection setup
- agent card fetches
- blocking vs streaming config
- text extraction from tasks and artifacts
- task id and context id tracking

### Minimal client

```python
import asyncio

from a2a_wrapper import AgentClient


async def main() -> None:
    async with AgentClient("http://localhost:10002") as client:
        reply = await client.send("Hello")
        print(reply.text)


asyncio.run(main())
```

## 9. Client concepts

### `AgentInfo`

Normalized agent card information.

```python
info = await client.get_agent_info()
print(info.name)
print(info.skills)
```

### `AgentResult`

Blocking send result.

Useful fields and helpers:

- `reply.task_id`
- `reply.context_id`
- `reply.state`
- `reply.text`
- `reply.is_complete`
- `reply.needs_input`
- `reply.is_failed`
- `reply.is_canceled`

### `StreamEvent`

Streaming event result.

Useful fields:

- `event.task_id`
- `event.context_id`
- `event.state`
- `event.text`
- `event.is_final`

### `Conversation`

Use this when you want multi-turn continuity.

```python
conversation = client.new_conversation()
first = await client.send("Hello", conversation=conversation)
second = await client.send("Continue", conversation=conversation)
```

## 10. Client usage patterns

### Get agent information

```python
info = await client.get_agent_info()
print(info)
```

### Send a blocking request

```python
reply = await client.send("Hello")
print(reply.state)
print(reply.text)
```

### Get only text

```python
text = await client.ask("Hello")
print(text)
```

### Stream responses

```python
async for event in client.stream("Hello"):
    if event.text:
        print(event.text)
    if event.is_final:
        break
```

### Collect a streamed response into one string

```python
text = await client.ask_stream("Hello")
print(text)
```

### Send metadata and history settings

```python
reply = await client.send(
    "Hello",
    history_length=10,
    metadata={"source": "web-app"},
)
```

### Fetch a task later

```python
task = await client.get_task(task_id)
```

### Cancel a task

```python
await client.cancel_task(task_id)
```

## 11. Sync helpers

For quick scripts and local tools:

```python
from a2a_wrapper import AgentClient


client = AgentClient("http://localhost:10002")
info = client.get_agent_info_sync()
reply = client.send_sync("Hello")

print(info.name)
print(reply.text)
```

These helpers call `asyncio.run(...)` internally, so they are best for scripts, not for code already running inside an event loop.

## 12. Real project structure

A practical app layout can look like this:

```text
my_project/
  pyproject.toml
  .env
  src/
    my_project/
      __init__.py
      capabilities.py
      server.py
      client_demo.py
      agents/
        support_agent.py
        research_agent.py
```

Suggested split:

- keep A2A transport code in one server module
- keep your framework or business logic in separate modules
- keep capabilities in a shared file when multiple services reuse them

## 13. LangChain example

This repository includes `examples/my_langchain_agent.py`.

That example does three things:

1. defines LangChain tools
2. builds a LangChain agent
3. exposes it through `create_agent_server(...)`

Typical handler shape:

```python
async def langchain_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.progress("LangChain agent is processing the request...")
    agent = build_langchain_agent(...)
    result = await agent.ainvoke({"input": request.user_text})
    await responder.complete(result.get("output", "No answer returned"))
```

Run it:

```bash
pip install "a2a-wrapper[langchain]"
python examples/my_langchain_agent.py
```

Test it:

```bash
a2a-wrapper-client --url http://localhost:10002 --msg "What is 27 * 3 + 4?"
```

If you use OpenAI-backed models, add a `.env` file:

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## 14. CrewAI example

This repository includes `examples/my_crewai_agent.py`.

That example:

1. builds a CrewAI workflow
2. receives A2A input through `AgentRequest`
3. runs the crew
4. returns the result through `ResponseContext`

Typical handler shape:

```python
async def crewai_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.progress("CrewAI is working on the request...")
    crew = build_research_crew(request.user_text)
    result = await crew.kickoff_async(inputs={"topic": request.user_text})
    await responder.complete(str(result))
```

Run it:

```bash
pip install "a2a-wrapper[crewai]"
python examples/my_crewai_agent.py
```

Test it:

```bash
a2a-wrapper-client --url http://localhost:10003 --msg "Artificial Intelligence" --stream
```

## 15. How this maps to the official SDK

This package wraps common SDK pieces. Under the hood, it still relies on the official A2A Python SDK.

Client side:

- `ClientFactory.connect(...)`
- `create_text_message_object(...)`
- `MessageSendConfiguration`

Server side:

- `AgentExecutor`
- `DefaultRequestHandler`
- `A2AStarletteApplication`
- `TaskUpdater`

That means:

- you still benefit from the official SDK behavior
- you write less plumbing code in your app
- you can drop down to lower-level SDK concepts if your project needs it

## 16. When to use this package

Use `a2a-wrapper` when:

- you want a cleaner API for app teams
- you expose multiple agents and want consistent patterns
- you use LangChain or CrewAI and do not want to repeat A2A boilerplate
- you want a readable client wrapper for Python apps and scripts

Use raw `a2a-sdk` when:

- you need low-level control over every server and client primitive
- you are building unusual transport or lifecycle behavior
- your team already prefers the raw SDK surface

## 17. Testing your integration

Run the repository tests:

```bash
pytest
```

A good app-level test strategy is:

1. unit test your agent logic without A2A
2. unit test your handler behavior
3. add one smoke test that boots the A2A server locally
4. verify the Python client can send and receive messages

## 18. Common mistakes

### Using the PyPI name in imports

Wrong:

```python
import a2a-wrapper
```

Correct:

```python
import a2a_wrapper
```

### Forgetting to send a terminal response

A handler must finish with a terminal state such as:

- `await responder.complete(...)`
- `await responder.require_input(...)`
- `await responder.failed(...)`
- `await responder.cancel(...)`

### Mixing sync helpers into async app code

If you are already inside `async def`, use the async methods, not `ask_sync()` or `send_sync()`.

## 19. Summary

`a2a-wrapper` is a practical layer for teams who want to work with A2A without writing the same SDK plumbing in every service.

Use it when you want:

- a small server adapter around your agent logic
- a small Python client around A2A agents
- cleaner code for real applications
