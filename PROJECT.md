# Project Comparison: Raw `a2a-sdk` vs `a2a-wrapper`

This document compares two ways of connecting LangChain and CrewAI projects with A2A:

1. using the raw official `a2a-sdk` directly
2. using this project, `a2a-wrapper`

The goal is to help you understand where this project actually helps, where it adds abstraction, and when you should prefer one approach over the other.

## 1. The problem both approaches are solving

Suppose you already have:

- a LangChain agent
- or a CrewAI crew

Now you want to:

- expose it as an A2A server
- call it from an A2A client
- support task lifecycle updates
- support agent card metadata
- keep the code understandable for your team

Both approaches can do that.

The difference is how much A2A plumbing you write yourself.

## 2. High-level comparison

| Area | Raw `a2a-sdk` | `a2a-wrapper` |
|------|---------------|---------------|
| Server setup | More verbose | Shorter and more guided |
| Client setup | More low-level | Simpler API |
| LangChain integration | You wire request parsing and task updates yourself | You mostly write the agent logic |
| CrewAI integration | You wire request parsing and task updates yourself | You mostly write the crew logic |
| Boilerplate | Higher | Lower |
| Flexibility | Maximum | High, but opinionated |
| Learning curve | Higher | Lower |
| Readability for teams | Depends on SDK familiarity | Usually better for app teams |
| Control over exact SDK primitives | Full | Still possible, but one layer removed |

## 3. What raw `a2a-sdk` typically looks like

If you use the official SDK directly, you usually need to deal with:

- `AgentExecutor`
- `RequestContext`
- `EventQueue`
- `TaskUpdater`
- `DefaultRequestHandler`
- `A2AStarletteApplication`
- `AgentCard`
- `AgentSkill`
- client-side connection objects
- message creation and configuration objects

### Server-side responsibilities with raw SDK

You usually write code for:

- reading incoming text from the A2A message parts
- creating or using `TaskUpdater`
- sending working state updates
- sending completion state updates
- sending failure state updates
- defining the agent card
- wiring the request handler
- wiring the ASGI app
- starting `uvicorn`

### Client-side responsibilities with raw SDK

You usually write code for:

- connecting with the SDK client
- creating message objects
- configuring blocking or streaming mode
- parsing returned task/message structures
- extracting text from task status or artifacts
- managing conversation context ids and task ids

## 4. What this project changes

This project keeps the official SDK underneath, but wraps the common repetitive parts.

### On the server side, this project gives you

- `AgentServerConfig`
- `AgentCapability`
- `AgentRequest`
- `ResponseContext`
- `create_agent_server(...)`

Instead of making you directly juggle all the lower-level A2A server pieces every time.

### On the client side, this project gives you

- `AgentClient`
- `AgentInfo`
- `AgentResult`
- `StreamEvent`
- `Conversation`

Instead of making you repeatedly normalize SDK event structures yourself.

## 5. LangChain comparison

## Raw `a2a-sdk` + LangChain

Typical flow:

1. create a LangChain agent
2. subclass or implement the A2A server executor interface
3. extract user text from `RequestContext.message.parts`
4. call `agent.ainvoke(...)`
5. push working/completed/failed states through `TaskUpdater`
6. manually build the A2A server app and handler

### Pros

- full control over every A2A detail
- easier if your team already knows the SDK deeply
- easier if you need unusual custom server behavior

### Cons

- more code
- more repeated plumbing
- more room for mistakes in request parsing and response state handling
- harder for non-A2A-specialist teammates to follow

## `a2a-wrapper` + LangChain

Typical flow:

1. create the LangChain agent
2. write a handler that receives `AgentRequest`
3. call `agent.ainvoke({"input": request.user_text})`
4. complete through `ResponseContext`
5. build the server with `create_agent_server(...)`

### Example shape

```python
async def langchain_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.progress("LangChain agent is processing the request...")
    result = await agent.ainvoke({"input": request.user_text})
    await responder.complete(result.get("output", "No answer returned"))
```

### Pros

- much less boilerplate
- request text is already normalized
- status methods are easier to read
- easier to hand off to app developers
- faster to create multiple A2A adapters

### Cons

- one extra abstraction layer
- if you need a very unusual A2A server workflow, you may still need raw SDK access

## Verdict for LangChain

If your goal is:

- expose LangChain agents quickly
- keep the code readable
- let teammates understand it without mastering the full A2A SDK first

then `a2a-wrapper` is usually the better fit.

If your goal is:

- build a highly customized A2A transport layer
- use uncommon SDK features directly everywhere

then raw `a2a-sdk` may be better.

## 6. CrewAI comparison

## Raw `a2a-sdk` + CrewAI

Typical flow:

1. build the crew
2. implement the A2A executor
3. extract request text manually
4. run `crew.kickoff_async(...)`
5. translate output into task updates
6. manually wire server metadata and app startup

### Pros

- maximum control
- no wrapper dependency

### Cons

- same A2A plumbing repeated again
- more code than the CrewAI logic itself in many simple cases

## `a2a-wrapper` + CrewAI

Typical flow:

1. build the crew
2. write a handler using `AgentRequest`
3. run `crew.kickoff_async(inputs={"topic": request.user_text})`
4. send the final output through `ResponseContext.complete(...)`

### Example shape

```python
async def crewai_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.progress("CrewAI is working on the request...")
    result = await crew.kickoff_async(inputs={"topic": request.user_text})
    await responder.complete(str(result))
```

### Pros

- very small amount of A2A-specific code
- CrewAI logic stays front and center
- easier to build many A2A-enabled crews

### Cons

- same wrapper abstraction tradeoff as with LangChain

## Verdict for CrewAI

For CrewAI especially, the wrapper tends to help a lot because multi-agent orchestration code is already complex enough. Reducing A2A transport boilerplate is a real win here.

## 7. Client comparison

## Raw `a2a-sdk` client usage

You still need to think about:

- connection creation
- card path
- message object creation
- streaming vs blocking config
- result normalization
- extracting final text from different SDK shapes
- tracking task ids and context ids

## `a2a-wrapper` client usage

You use:

```python
async with AgentClient("http://localhost:10002") as client:
    reply = await client.send("Hello")
    print(reply.text)
```

And for multi-turn:

```python
conversation = client.new_conversation()
reply = await client.send("Hello", conversation=conversation)
```

### Why the wrapper client helps

- simpler mental model
- normalized response object
- fewer SDK internals exposed at call sites
- easier streaming consumption
- easier sync helper methods for scripts

## 8. Boilerplate comparison

## Raw `a2a-sdk`

You usually write more code around:

- server startup
- request parsing
- state updates
- artifact handling
- result extraction
- client event normalization

## `a2a-wrapper`

You usually write more code around:

- actual agent logic
- prompts
- tools
- LangChain or CrewAI behavior

That is usually a better place to spend complexity.

## 9. Functional coverage comparison

This wrapper now includes support for a broader set of task lifecycle actions.

### Current `ResponseContext` methods in this project

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

### Current `AgentClient` methods in this project

- `get_agent_info(...)`
- `send(...)`
- `ask(...)`
- `stream(...)`
- `ask_stream(...)`
- `get_task(...)`
- `cancel_task(...)`
- sync helpers for common usage

So the wrapper is no longer just a tiny simplified shell. It now covers a meaningful set of real workflow needs while keeping the API friendlier.

## 10. Complexity comparison

You mentioned an important concern: whether the wrapper reduced functionality while increasing complexity.

That can happen if a wrapper:

- renames too much
- hides too much
- removes useful SDK primitives
- adds abstraction without giving enough convenience back

This project should avoid that by following this rule:

- expose friendly names for common tasks
- keep compatibility aliases
- keep the underlying A2A model visible enough
- expose enough task lifecycle operations to stay useful

### Current balance of this project

Compared to the earliest version, this project now has:

- better public naming
- broader task lifecycle methods
- better client convenience
- clearer docs

So the abstraction is a little bigger, but it is also more capable and easier to explain.

## 11. When to choose raw `a2a-sdk`

Choose raw SDK if:

- you need absolute control over every A2A primitive
- you are implementing unusual transport or server behavior
- your team is already comfortable with the SDK internals
- you do not want any wrapper dependency

## 12. When to choose `a2a-wrapper`

Choose this project if:

- you want to adapt many LangChain or CrewAI agents quickly
- you want a cleaner application-facing API
- you want to reduce repetitive A2A plumbing
- you want junior or app-focused developers to understand the code faster
- you want a reusable internal or public package

## 13. Honest tradeoff summary

### Raw `a2a-sdk`

- strongest control
- most explicit
- highest boilerplate
- hardest to standardize across many projects

### `a2a-wrapper`

- slightly more abstraction
- much better day-to-day ergonomics
- better reusability
- easier onboarding
- still built on the official SDK, not a custom protocol

## 14. Practical recommendation for this project

For your goal, which is:

- making it easy for people to convert existing agents into A2A servers and clients
- supporting LangChain and CrewAI
- letting others install and use it like a normal package

this wrapper approach is the right direction.

The important thing is not to make it too magical.

The best version of this package is:

- easy to import
- easy to explain
- still close enough to the official SDK model
- rich enough for real projects

That is the direction this project is now moving toward.
