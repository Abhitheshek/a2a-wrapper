# a2a-wrapper

`a2a-wrapper` is a lightweight helper layer for exposing custom agents as A2A servers and consuming A2A agents through the official Python `a2a-sdk`.

It is designed for teams who want a faster path from agent logic to an A2A-compatible service without rewriting the same request parsing, task response, and client plumbing every time.

## What it includes

- `src/a2a_wrapper/`
  - installable package with client and server APIs
- `examples/`
  - ready-to-run LangChain and CrewAI sample servers
- `tests/`
  - helper tests and an optional end-to-end smoke test

## Install

Base install:

```bash
pip install -e .
```

Optional extras:

```bash
pip install -e .[langchain]
pip install -e .[crewai]
pip install -e .[dev]
```

## Quick example

```python
from a2a_wrapper import (
    AgentCapability,
    AgentRequest,
    AgentServerConfig,
    ResponseContext,
    create_agent_server,
)


async def handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.complete(f"Echo: {request.user_text}")


server = create_agent_server(
    config=AgentServerConfig(
        name="Echo Agent",
        description="Simple echo agent",
        host="0.0.0.0",
        port=10002,
    ),
    capabilities=[
        AgentCapability(
            capability_id="echo",
            name="Echo",
            description="Echoes user input",
        )
    ],
    handler=handler,
)

server.run()
```

## Client example

```python
import asyncio

from a2a_wrapper import AgentClient


async def main():
    async with AgentClient("http://localhost:10002") as client:
        reply = await client.send("Hello")
        print(reply.text)


asyncio.run(main())
```

## Examples

See [examples/README.md](C:\Users\ay936\Downloads\a2a_wrapper\examples\README.md) for exact run steps.

## Docs

See [DOCS.md](C:\Users\ay936\Downloads\a2a_wrapper\DOCS.md) for detailed LangChain, CrewAI, server, and client walkthroughs.

## Testing

Run:

```bash
pytest
```

Notes:

- unit tests work without a live A2A server
- the smoke test runs only when `a2a-sdk` is installed and importable
