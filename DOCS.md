# a2a-wrapper Detailed Guide

This guide matches the current project exactly.

Current package details:

- distribution name: `a2a-wrapper`
- import name: `a2a_wrapper`
- package source: `src/a2a_wrapper/`

Current project folders:

- `src/a2a_wrapper/`
- `examples/`
- `tests/`

This package is meant to make two things easier:

1. exposing your own agent logic as an A2A server
2. calling A2A servers through a clean Python client

## 1. Public API of this project

For new code, use these names:

```python
from a2a_wrapper import (
    AgentClient,
    AgentServer,
    AgentServerConfig,
    AgentCapability,
    AgentRequest,
    ResponseContext,
    AgentResult,
    StreamEvent,
    Conversation,
    create_agent_server,
)
```

This project also keeps backward-compatible aliases for older names:

- `A2AAgentClient`
- `A2AServerLauncher`
- `A2ARequest`
- `AgentProfile`
- `AgentSkillCard`
- `TaskResponder`
- `create_server`

If you are starting fresh, prefer the newer names because they are easier to understand in normal Python code.

## 2. Installation

### Base package

```bash
pip install -e .
```

### LangChain support

```bash
pip install -e .[langchain]
```

### CrewAI support

```bash
pip install -e .[crewai]
```

### Dev tools

```bash
pip install -e .[dev]
```

## 3. Project structure in this repo

Current implementation files:

- `src/a2a_wrapper/_client.py`
  - client wrapper built on top of the official A2A SDK client
- `src/a2a_wrapper/_server.py`
  - server wrapper built on top of the official A2A SDK server APIs
- `src/a2a_wrapper/__init__.py`
  - package exports
- `examples/my_langchain_agent.py`
  - LangChain A2A server example
- `examples/my_crewai_agent.py`
  - CrewAI A2A server example

## 4. Core concepts

### `AgentServerConfig`

This defines:

- server name
- description
- host
- port
- version
- streaming capability
- docs URL

Example:

```python
config = AgentServerConfig(
    name="LangChain Math Agent",
    description="A LangChain agent exposed as an A2A server",
    host="0.0.0.0",
    port=10002,
)
```

### `AgentCapability`

This describes what your server can do in the A2A agent card.

Example:

```python
capability = AgentCapability(
    capability_id="math_reasoning",
    name="Math Reasoning",
    description="Solves math and basic text requests",
    tags=["math", "tool-use"],
    examples=["What is 2 + 2?", "Count the words in this sentence"],
)
```

### `AgentRequest`

This is what your handler receives.

Important fields:

- `request.user_text`
- `request.task_id`
- `request.context_id`
- `request.message_id`
- `request.raw_context`
- `request.raw_message`
- `request.metadata`

In most handlers, `request.user_text` is the main input you need.

### `ResponseContext`

This is what your handler uses to send updates back to the A2A client.

Useful methods:

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

These map to the official A2A task lifecycle and make the wrapper more complete and easier to use.

### `AgentClient`

This is the client wrapper.

Useful methods:

- `await client.get_agent_info()`
- `await client.send(text, ...)`
- `await client.ask(text, ...)`
- `await client.stream(text, ...)`
- `await client.ask_stream(text, ...)`
- `await client.get_task(task_id, ...)`
- `await client.cancel_task(task_id)`
- `client.new_conversation()`

Sync helpers:

- `client.ask_sync(...)`
- `client.send_sync(...)`
- `client.get_agent_info_sync()`
- `client.get_task_sync(...)`
- `client.cancel_task_sync(...)`

## 5. Minimal server example

This is the simplest possible server pattern in the current package:

```python
from a2a_wrapper import (
    AgentCapability,
    AgentRequest,
    AgentServerConfig,
    ResponseContext,
    create_agent_server,
)


async def echo_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.progress("Processing request...")
    await responder.complete(f"Echo: {request.user_text}")


server = create_agent_server(
    config=AgentServerConfig(
        name="Echo Agent",
        description="Simple echo server",
        host="0.0.0.0",
        port=10002,
    ),
    capabilities=[
        AgentCapability(
            capability_id="echo",
            name="Echo",
            description="Repeats the user input",
        )
    ],
    handler=echo_handler,
)


if __name__ == "__main__":
    server.run()
```

## 6. Minimal client example

```python
import asyncio

from a2a_wrapper import AgentClient


async def main():
    async with AgentClient("http://localhost:10002") as client:
        info = await client.get_agent_info()
        print(info)

        reply = await client.send("Hello")
        print(reply.text)


asyncio.run(main())
```

## 7. LangChain example in this project

This repo already contains:

- `examples/my_langchain_agent.py`

That file uses:

- `ChatOpenAI`
- LangChain tools
- `create_react_agent(...)`
- `AgentExecutor.ainvoke(...)`
- the wrapper’s `create_agent_server(...)`

### Current LangChain flow in this repo

1. build the LangChain agent
2. receive A2A input through `AgentRequest`
3. pass `request.user_text` to LangChain
4. return the output through `ResponseContext.complete(...)`

### Core handler pattern

```python
async def langchain_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.progress("LangChain agent is processing the request...")

    agent = build_langchain_agent(...)
    result = await agent.ainvoke({"input": request.user_text})
    answer = result.get("output", "No answer returned")

    await responder.complete(answer)
```

### Why this works

The wrapper takes care of:

- agent card generation
- request parsing
- task status updates
- final result publishing

So your LangChain code only needs to focus on:

- building the agent
- passing input
- returning output

### Run the LangChain example

```bash
pip install -e .[langchain]
python examples/my_langchain_agent.py
```

Default server URL:

```text
http://localhost:10002
```

### Test the LangChain example

With the installed console script:

```bash
a2a-wrapper-client --url http://localhost:10002 --msg "What is 27 * 3 + 4?"
```

Or with the module path:

```bash
python -m a2a_wrapper._client --url http://localhost:10002 --msg "What is 27 * 3 + 4?"
```

### Environment for LangChain example

If you use OpenAI-backed LangChain components, create a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## 8. CrewAI example in this project

This repo already contains:

- `examples/my_crewai_agent.py`

That file uses:

- `Agent`
- `Crew`
- `Task`
- `Process`
- `kickoff_async(...)`
- the wrapper’s `create_agent_server(...)`

### Current CrewAI flow in this repo

1. build a CrewAI crew
2. receive A2A input through `AgentRequest`
3. pass `request.user_text` into the crew
4. return the final result through `ResponseContext.complete(...)`

### Core handler pattern

```python
async def crewai_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.progress("CrewAI is working on the request...")

    crew = build_research_crew(request.user_text)
    result = await crew.kickoff_async(inputs={"topic": request.user_text})

    await responder.complete(str(result))
```

### Run the CrewAI example

```bash
pip install -e .[crewai]
python examples/my_crewai_agent.py
```

Default server URL:

```text
http://localhost:10003
```

### Test the CrewAI example

```bash
a2a-wrapper-client --url http://localhost:10003 --msg "Artificial Intelligence" --stream
```

Or:

```bash
python -m a2a_wrapper._client --url http://localhost:10003 --msg "Artificial Intelligence" --stream
```

## 9. Reusing conversations on the client

If you want multiple messages to stay in the same logical task context, use a `Conversation`.

```python
import asyncio

from a2a_wrapper import AgentClient


async def main():
    async with AgentClient("http://localhost:10002") as client:
        conversation = client.new_conversation()

        first = await client.send("Hello", conversation=conversation)
        second = await client.send(
            "Continue from the previous message",
            conversation=conversation,
        )

        print(first.text)
        print(second.text)


asyncio.run(main())
```

## 10. Blocking vs streaming

### Blocking

Use:

```python
reply = await client.send("Hello")
```

You receive a final `AgentResult`.

### Streaming

Use:

```python
async for event in client.stream("Hello"):
    ...
```

You receive `StreamEvent` objects, which can carry intermediate working states and the final result.

### Collecting a full streamed result

Use:

```python
text = await client.ask_stream("Hello")
```

## 11. Request metadata and history length

The client wrapper supports additional send/stream parameters:

```python
reply = await client.send(
    "Hello",
    history_length=10,
    metadata={"source": "web-app"},
)
```

And:

```python
async for event in client.stream(
    "Hello",
    history_length=10,
    metadata={"source": "cli"},
):
    ...
```

This makes it easier to preserve extra request context or control how much task history is requested from the server.

## 12. Richer response states

`AgentResult` includes these useful checks:

- `reply.is_complete`
- `reply.needs_input`
- `reply.is_failed`
- `reply.is_canceled`

Example:

```python
reply = await client.send("Hello")

if reply.needs_input:
    print("Agent asked for more input")
elif reply.is_failed:
    print("Agent failed")
elif reply.is_complete:
    print("Agent completed")
```

## 13. More complete responder methods

Because the wrapper now exposes more of the official task lifecycle, your handler can be more expressive.

### Ask the user for more input

```python
async def handler(request, responder):
    if not request.user_text.strip():
        await responder.require_input("Please send a non-empty prompt.")
        return
    await responder.complete("Thanks")
```

### Mark as submitted before work starts

```python
async def handler(request, responder):
    await responder.submit("Task received and queued.")
    await responder.progress("Processing...")
    await responder.complete("Done")
```

### Require authentication

```python
async def handler(request, responder):
    await responder.require_auth("Please authenticate before using this agent.")
```

### Reject a request

```python
async def handler(request, responder):
    await responder.reject("This request type is not supported.")
```

### Cancel a task

```python
async def handler(request, responder):
    await responder.cancel("Task cancelled by server logic.")
```

### Add an artifact before completion

```python
async def handler(request, responder):
    await responder.add_text_artifact("Intermediate artifact data")
    await responder.complete("Final response")
```

## 14. Mapping to the official A2A SDK

This wrapper is not replacing the A2A SDK. It is built on top of it.

Client side:

- official SDK connection uses `ClientFactory.connect(...)`
- message creation uses `create_text_message_object(...)`
- send configuration uses `MessageSendConfiguration`

Server side:

- custom handlers sit on top of `AgentExecutor`
- app creation uses `A2AStarletteApplication`
- request handling uses `DefaultRequestHandler`
- response lifecycle uses `TaskUpdater`

The official Python SDK docs expose these pieces:

- [a2a package docs](https://a2a-protocol.org/latest/sdk/python/api/a2a.html)
- [a2a.server package docs](https://a2a-protocol.org/latest/sdk/python/api/a2a.server.html)
- [TaskUpdater docs](https://a2a-protocol.org/latest/sdk/python/api/a2a.server.tasks.task_updater.html)

From the `TaskUpdater` docs, the official SDK supports operations such as `requires_input`, `start_work`, `submit`, `requires_auth`, and `reject`, and this wrapper now exposes those ideas in `ResponseContext`. The server package docs also document the server-side pieces like `AgentExecutor` and `DefaultRequestHandler`, which are what this wrapper is building on top of.

## 15. Current package-specific commands

Install package:

```bash
pip install -e .
```

Run tests:

```bash
pytest
```

Run LangChain example:

```bash
pip install -e .[langchain]
python examples/my_langchain_agent.py
```

Run CrewAI example:

```bash
pip install -e .[crewai]
python examples/my_crewai_agent.py
```

Call the console script:

```bash
a2a-wrapper-client --url http://localhost:10002 --msg "Hello"
```

## 16. Current file references

- package exports: [__init__.py](C:\Users\ay936\Downloads\a2a_wrapper\src\a2a_wrapper\__init__.py)
- client wrapper: [_client.py](C:\Users\ay936\Downloads\a2a_wrapper\src\a2a_wrapper\_client.py)
- server wrapper: [_server.py](C:\Users\ay936\Downloads\a2a_wrapper\src\a2a_wrapper\_server.py)
- LangChain example: [my_langchain_agent.py](C:\Users\ay936\Downloads\a2a_wrapper\examples\my_langchain_agent.py)
- CrewAI example: [my_crewai_agent.py](C:\Users\ay936\Downloads\a2a_wrapper\examples\my_crewai_agent.py)
- examples quick guide: [README.md](C:\Users\ay936\Downloads\a2a_wrapper\examples\README.md)

## 17. Practical recommendation

If you are building a real project with this wrapper:

- keep your own agent code separate from the wrapper package
- let the wrapper handle transport and A2A glue
- keep your LangChain or CrewAI business logic inside your own module
- add tests for your handlers
- pin your framework versions
- decide how you want task persistence, auth, and deployment to work

This package should make the A2A layer easier, not hide your actual agent architecture.
