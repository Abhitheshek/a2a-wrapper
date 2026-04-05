# Examples

This folder contains ready-to-run sample agents that show how to expose framework-based agents as A2A servers using the wrapper.

## Files

- `my_langchain_agent.py`: LangChain example server on port `10002`
- `my_crewai_agent.py`: CrewAI example server on port `10003`

## Install

Base dependencies:

```bash
pip install "a2a-sdk[http-server]" httpx uvicorn
```

LangChain example:

```bash
pip install langchain langchain-openai langgraph langchain-community python-dotenv
```

CrewAI example:

```bash
pip install crewai crewai-tools python-dotenv
```

## Optional environment

If your framework agent needs model credentials, create a `.env` file in the project root.

Example:

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## Run the LangChain example

```bash
python examples/my_langchain_agent.py
```

Test it:

```bash
a2a-wrapper-client --url http://localhost:10002 --msg "What is 27 * 3 + 4?"
```

## Run the CrewAI example

```bash
python examples/my_crewai_agent.py
```

Test it:

```bash
a2a-wrapper-client --url http://localhost:10003 --msg "Artificial Intelligence" --stream
```

## Notes

- The examples already use `from a2a_wrapper import AgentClient, AgentServerConfig, AgentCapability, create_agent_server, ...`.
- Run them from the repository root after `pip install -e .` so Python can resolve the package cleanly.
