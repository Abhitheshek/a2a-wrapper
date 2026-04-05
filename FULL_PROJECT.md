# Full Project Template: LangChain and CrewAI with `a2a-wrapper`

This document gives you a copy-paste-friendly project template that shows how to:

- build a LangChain A2A server
- build a CrewAI A2A server
- call both from an A2A client
- organize the code in a real project structure

This template is designed for the current package in this repository.

Use these public imports:

```python
from a2a_wrapper import (
    AgentClient,
    AgentServerConfig,
    AgentCapability,
    AgentRequest,
    ResponseContext,
    create_agent_server,
)
```

## 1. Why this template exists

If you try to connect LangChain or CrewAI directly with raw `a2a-sdk`, you usually end up writing the same transport glue again and again:

- agent card setup
- request parsing
- task updates
- status transitions
- client normalization

This project template keeps the framework logic in your app code and the A2A glue in `a2a-wrapper`.

## 2. Current framework direction

This template follows the current direction from the docs:

- LangChain:
  - use modern constructor helpers like `create_react_agent(...)`
  - avoid old deprecated agent type enums and deprecated conversational agent classes
  - note: LangChain docs also indicate that newer agent work increasingly moves toward LangGraph for advanced workflows
- CrewAI:
  - use `Agent`, `Task`, `Crew`, and `Process`
  - run with `kickoff_async(...)` when you want async integration
- A2A:
  - keep using the official A2A SDK underneath
  - let `a2a-wrapper` reduce the repetitive wiring

## 3. Suggested project structure

```text
my_ai_project/
  .env
  pyproject.toml
  src/
    my_ai_project/
      __init__.py
      common.py
      langchain_server.py
      crewai_server.py
      client_demo.py
```

## 4. Installation

If `a2a-wrapper` is published:

```bash
pip install a2a-wrapper
```

If you are developing locally with this repository:

```bash
pip install -e .[langchain]
pip install -e .[crewai]
```

You will also want a `.env` file:

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## 5. Shared common file

Create `src/my_ai_project/common.py`

```python
from __future__ import annotations

from a2a_wrapper import AgentCapability


LANGCHAIN_CAPABILITIES = [
    AgentCapability(
        capability_id="langchain_reasoning",
        name="LangChain Reasoning",
        description="Performs reasoning with tools using LangChain",
        tags=["langchain", "tools", "reasoning"],
        examples=[
            "What is 27 * 3 + 4?",
            "Count the words in 'hello world from A2A'",
        ],
    )
]


CREWAI_CAPABILITIES = [
    AgentCapability(
        capability_id="crewai_research",
        name="CrewAI Research",
        description="Runs a CrewAI research and writing workflow",
        tags=["crewai", "research", "multi-agent"],
        examples=[
            "Artificial Intelligence",
            "Climate change",
        ],
    )
]
```

## 6. Full LangChain server

Create `src/my_ai_project/langchain_server.py`

```python
from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from a2a_wrapper import (
    AgentRequest,
    AgentServerConfig,
    ResponseContext,
    create_agent_server,
)
from my_ai_project.common import LANGCHAIN_CAPABILITIES


load_dotenv()


@tool
def calculator(expression: str) -> str:
    """Evaluate a simple math expression."""
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as exc:
        return f"Calculation error: {exc}"


@tool
def word_counter(text: str) -> str:
    """Count words and characters in text."""
    return f"Words: {len(text.split())}, Characters: {len(text)}"


def build_langchain_agent(model_name: str = "gpt-4o-mini") -> AgentExecutor:
    llm = ChatOpenAI(model=model_name, temperature=0)
    tools = [calculator, word_counter]

    prompt = PromptTemplate.from_template(
        "You are a helpful assistant.\n"
        "Always respond in the same language as the user.\n\n"
        "You can use the following tools:\n"
        "{tools}\n\n"
        "Available tool names: {tool_names}\n\n"
        "Use this format:\n"
        "Question: the question to answer\n"
        "Thought: think about what to do\n"
        "Action: the action to take, one of [{tool_names}]\n"
        "Action Input: the input to the action\n"
        "Observation: the result of the action\n"
        "... repeat as needed ...\n"
        "Thought: I now know the final answer\n"
        "Final Answer: the final answer\n\n"
        "Question: {input}\n"
        "Thought:{agent_scratchpad}"
    )

    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
    )


async def langchain_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.submit("LangChain task accepted.")
    await responder.progress("LangChain agent is processing the request...")

    agent = build_langchain_agent(
        model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    )
    result = await agent.ainvoke({"input": request.user_text})

    answer = result.get("output", "No answer returned.")
    await responder.complete(answer)


server = create_agent_server(
    config=AgentServerConfig(
        name="LangChain A2A Server",
        description="LangChain reasoning server exposed through A2A",
        host="0.0.0.0",
        port=10002,
    ),
    capabilities=LANGCHAIN_CAPABILITIES,
    handler=langchain_handler,
)


if __name__ == "__main__":
    server.run()
```

## 7. Full CrewAI server

Create `src/my_ai_project/crewai_server.py`

```python
from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.tools import BaseTool

from a2a_wrapper import (
    AgentRequest,
    AgentServerConfig,
    ResponseContext,
    create_agent_server,
)
from my_ai_project.common import CREWAI_CAPABILITIES


class ResearchSummaryTool(BaseTool):
    name: str = "Research Summary Tool"
    description: str = "Creates a structured summary for a research topic"

    def _run(self, topic: str) -> str:
        return (
            f"Topic: {topic}\n"
            f"- Overview: short structured summary\n"
            f"- Key ideas: major concepts\n"
            f"- Use cases: practical applications\n"
            f"- Risks: limitations and concerns\n"
            f"- Next steps: what to explore further"
        )


def build_research_crew(topic: str) -> Crew:
    researcher = Agent(
        role="Research Analyst",
        goal=f"Research the topic: {topic}",
        backstory="You are a careful research analyst who summarizes topics clearly.",
        tools=[ResearchSummaryTool()],
        verbose=True,
        allow_delegation=False,
    )

    writer = Agent(
        role="Report Writer",
        goal="Turn research into a structured and readable report",
        backstory="You write concise, useful, and clean reports.",
        verbose=True,
        allow_delegation=False,
    )

    reviewer = Agent(
        role="Quality Reviewer",
        goal="Review the final report for clarity and completeness",
        backstory="You check structure, quality, and readability.",
        verbose=True,
        allow_delegation=False,
    )

    research_task = Task(
        description=f"Research the topic: {topic}",
        expected_output="Structured topic summary",
        agent=researcher,
    )

    writing_task = Task(
        description="Turn the research into a clear report with sections",
        expected_output="Readable report",
        agent=writer,
        context=[research_task],
    )

    review_task = Task(
        description="Review the report and improve quality if needed",
        expected_output="Reviewed final report",
        agent=reviewer,
        context=[writing_task],
    )

    return Crew(
        agents=[researcher, writer, reviewer],
        tasks=[research_task, writing_task, review_task],
        process=Process.sequential,
        verbose=True,
    )


async def crewai_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.submit("CrewAI task accepted.")
    await responder.progress("CrewAI is working on the request...")

    crew = build_research_crew(request.user_text)
    result = await crew.kickoff_async(inputs={"topic": request.user_text})

    await responder.complete(str(result))


server = create_agent_server(
    config=AgentServerConfig(
        name="CrewAI A2A Server",
        description="CrewAI research workflow exposed through A2A",
        host="0.0.0.0",
        port=10003,
    ),
    capabilities=CREWAI_CAPABILITIES,
    handler=crewai_handler,
)


if __name__ == "__main__":
    server.run()
```

## 8. Full client example

In this version, the client demo does two useful things:

- runs an interactive loop
- treats the CrewAI A2A server as a tool that can be called from the LangChain side

This is a stronger real-world pattern because one A2A-exposed agent can call another A2A-exposed agent.

Create `src/my_ai_project/client_demo.py`

```python
from __future__ import annotations

import asyncio

from a2a_wrapper import AgentClient


async def show_agent_info() -> None:
    async with AgentClient("http://localhost:10002") as langchain_client:
        info = await langchain_client.get_agent_info()
        print("LangChain server info:")
        print(info)
        print()

    async with AgentClient("http://localhost:10003") as crewai_client:
        info = await crewai_client.get_agent_info()
        print("CrewAI server info:")
        print(info)
        print()


async def interactive_loop() -> None:
    print("Interactive A2A demo started.")
    print("Type 'exit' to quit.")
    print()

    async with AgentClient("http://localhost:10002") as langchain_client:
        conversation = langchain_client.new_conversation()

        while True:
            user_input = input("You > ").strip()

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit"}:
                print("Exiting interactive demo.")
                break

            reply = await langchain_client.send(
                user_input,
                conversation=conversation,
            )

            print("LangChain A2A Agent >")
            print(reply.text)
            print()


async def main() -> None:
    await show_agent_info()
    await interactive_loop()


if __name__ == "__main__":
    asyncio.run(main())
```

## 9. Make the CrewAI server available as a tool inside the LangChain server

If you want the LangChain A2A server to call the CrewAI A2A server as a tool, update the LangChain server code.

This is the most interesting setup in a multi-agent A2A architecture:

- LangChain server stays the main reasoning interface
- CrewAI server becomes a specialist agent
- LangChain uses the CrewAI A2A server as one of its tools

Replace the LangChain server file with this version:

```python
from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from a2a_wrapper import (
    AgentCapability,
    AgentClient,
    AgentRequest,
    AgentServerConfig,
    ResponseContext,
    create_agent_server,
)


load_dotenv()


@tool
def calculator(expression: str) -> str:
    """Evaluate a simple math expression."""
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as exc:
        return f"Calculation error: {exc}"


@tool
def word_counter(text: str) -> str:
    """Count words and characters in text."""
    return f"Words: {len(text.split())}, Characters: {len(text)}"


@tool
def call_crewai_research_server(topic: str) -> str:
    """Call the CrewAI A2A server as a research tool."""

    async def _run() -> str:
        async with AgentClient("http://localhost:10003") as crewai_client:
            return await crewai_client.ask(topic)

    return asyncio.run(_run())


def build_langchain_agent(model_name: str = "gpt-4o-mini") -> AgentExecutor:
    llm = ChatOpenAI(model=model_name, temperature=0)
    tools = [calculator, word_counter, call_crewai_research_server]

    prompt = PromptTemplate.from_template(
        "You are a helpful assistant.\n"
        "Always respond in the same language as the user.\n\n"
        "You can use the following tools:\n"
        "{tools}\n\n"
        "Available tool names: {tool_names}\n\n"
        "Use this format:\n"
        "Question: the question to answer\n"
        "Thought: think about what to do\n"
        "Action: the action to take, one of [{tool_names}]\n"
        "Action Input: the input to the action\n"
        "Observation: the result of the action\n"
        "... repeat as needed ...\n"
        "Thought: I now know the final answer\n"
        "Final Answer: the final answer\n\n"
        "Question: {input}\n"
        "Thought:{agent_scratchpad}"
    )

    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
    )


async def langchain_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.submit("LangChain task accepted.")
    await responder.progress("LangChain agent is processing the request...")

    agent = build_langchain_agent(
        model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    )
    result = await agent.ainvoke({"input": request.user_text})

    answer = result.get("output", "No answer returned.")
    await responder.complete(answer)


server = create_agent_server(
    config=AgentServerConfig(
        name="LangChain A2A Server",
        description="LangChain reasoning server exposed through A2A",
        host="0.0.0.0",
        port=10002,
    ),
    capabilities=[
        AgentCapability(
            capability_id="langchain_reasoning",
            name="LangChain Reasoning",
            description="Performs reasoning with tools and can call the CrewAI A2A server",
            tags=["langchain", "tools", "a2a", "crewai"],
            examples=[
                "What is 27 * 3 + 4?",
                "Research Artificial Intelligence and summarize the result",
            ],
        )
    ],
    handler=langchain_handler,
)


if __name__ == "__main__":
    server.run()
```

### How this architecture works

In this setup:

- the user talks to the LangChain A2A server on port `10002`
- the LangChain agent decides whether it needs the CrewAI research tool
- if needed, it calls `call_crewai_research_server(...)`
- that tool internally opens an `AgentClient` connection to `http://localhost:10003`
- the CrewAI A2A server returns a result
- LangChain uses that result inside its reasoning flow
- LangChain returns the final answer to the original user

So now the architecture is:

```text
User
  -> LangChain A2A Server
      -> CrewAI A2A Server (as a tool)
  -> Final answer
```

This is a strong example of using A2A servers as reusable agent services rather than isolated demos.

## 10. How to run this full project

From your project root:

### Install dependencies

```bash
pip install a2a-wrapper
pip install langchain langchain-openai langchain-community langgraph python-dotenv
pip install crewai crewai-tools python-dotenv
```

If you are using this repository directly instead of PyPI:

```bash
pip install -e .[langchain]
pip install -e .[crewai]
```

### Start the LangChain server

```bash
python -m my_ai_project.langchain_server
```

### Start the CrewAI server

In another terminal:

```bash
python -m my_ai_project.crewai_server
```

### Run the client

In another terminal:

```bash
python -m my_ai_project.client_demo
```

## 11. CLI-based quick testing

If `a2a-wrapper` is installed, you can also test with the built-in console script.

### Test LangChain server

```bash
a2a-wrapper-client --url http://localhost:10002 --msg "What is 12 * 9?"
```

### Test CrewAI server

```bash
a2a-wrapper-client --url http://localhost:10003 --msg "Climate change" --stream
```

## 12. What the wrapper is doing for you

### On the server side

Instead of manually wiring:

- `AgentExecutor`
- `RequestContext`
- `TaskUpdater`
- `DefaultRequestHandler`
- `A2AStarletteApplication`
- `uvicorn`

you mostly write:

- your framework agent logic
- one clean handler
- one config object
- one capability list

### On the client side

Instead of manually handling:

- SDK client connection
- message object creation
- result normalization
- text extraction from tasks/artifacts
- task and context id management

you use:

- `AgentClient`
- `AgentResult`
- `StreamEvent`
- `Conversation`

## 13. Richer responder methods you can use

Your handler is not limited to only `progress()` and `complete()`.

You can also use:

```python
await responder.submit("Task accepted.")
await responder.require_input("Please send a valid prompt.")
await responder.require_auth("Authentication required.")
await responder.reject("Unsupported request.")
await responder.cancel("Cancelled by policy.")
await responder.failed("Unexpected error.")
await responder.add_text_artifact("Intermediate text artifact")
```

This makes the wrapper useful for more realistic workflows than just simple one-shot completion.

## 14. Richer client methods you can use

The client also supports more than simple blocking calls.

Examples:

```python
reply = await client.send(
    "Hello",
    history_length=10,
    metadata={"source": "api"},
)
```

```python
text = await client.ask_stream("Tell me about AI")
```

```python
task = await client.get_task(task_id)
await client.cancel_task(task_id)
```

Sync helpers:

```python
client = AgentClient("http://localhost:10002")
info = client.get_agent_info_sync()
reply = client.send_sync("Hello")
```

## 15. Notes about “latest code”

This template is written to follow the current direction of the official docs:

- LangChain:
  - use constructor helpers like `create_react_agent(...)`
  - avoid deprecated old agent enums and deprecated conversational agent classes
- CrewAI:
  - use `Agent`, `Task`, `Crew`, `Process`
  - use `kickoff_async(...)` when integrating with async server code
- A2A:
  - keep the official A2A SDK underneath
  - let the wrapper provide the developer-friendly surface

LangChain docs also note that newer agent work increasingly points toward LangGraph for advanced workflows. For many straightforward tool-using agent cases, `create_react_agent(...)` is still a reasonable pattern and is much easier to copy-paste into an A2A adapter.

## 16. When to copy this template as-is

Use this template directly when:

- you want a working starting point
- your project mostly exchanges text
- you want separate servers for different frameworks
- you want a simple client demo for testing

## 17. When to customize it

You should customize this template when:

- your LangChain agent needs persistent memory
- your CrewAI workflow needs external tools or APIs
- you need authentication and authorization
- you need persistent task storage
- you want structured JSON output instead of only text
- you want deployment-ready logging and observability

## 18. Final takeaway

Raw `a2a-sdk` gives maximum control, but you write more A2A boilerplate.

This wrapper keeps the official SDK underneath but lets you focus on:

- LangChain logic
- CrewAI logic
- user-facing capabilities
- cleaner server/client code

If your goal is “make it easy for teams to expose existing agents as A2A services,” this full project shape is the right direction.
