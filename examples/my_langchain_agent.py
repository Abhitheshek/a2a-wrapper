from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain.agents import AgentExecutor as LCAgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from a2a_wrapper import (
    AgentCapability,
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
        return str(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307
    except Exception as exc:
        return f"Calculation error: {exc}"


@tool
def word_counter(text: str) -> str:
    """Count words and characters in a text."""
    return f"Words: {len(text.split())}, Characters: {len(text)}"


def build_langchain_agent(model_name: str = "gpt-4o-mini") -> LCAgentExecutor:
    llm = ChatOpenAI(model=model_name, temperature=0)
    tools = [calculator, word_counter]
    prompt = PromptTemplate.from_template(
        "You are a helpful assistant.\n"
        "Always respond in the same language as the user.\n\n"
        "Tools:\n{tools}\n\n"
        "Tool names: {tool_names}\n\n"
        "Question: {input}\n\n"
        "Thought: {agent_scratchpad}"
    )
    agent = create_react_agent(llm, tools, prompt)
    return LCAgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
    )


async def langchain_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.progress("LangChain agent request process kar raha hai...")
    agent = build_langchain_agent(model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    result = await agent.ainvoke({"input": request.user_text})
    await responder.complete(result.get("output", "No answer returned"))


server = create_agent_server(
    config=AgentServerConfig(
        name="LangChain Math Agent",
        description="LangChain ReAct agent exposed as an A2A server",
        host="0.0.0.0",
        port=10002,
    ),
    capabilities=[
        AgentCapability(
            capability_id="math_reasoning",
            name="Math Reasoning",
            description="Solves math and simple text analysis tasks",
            tags=["langchain", "math", "text"],
            examples=["2 + 2 kya hai?", "hello world mein kitne words hain?"],
        )
    ],
    handler=langchain_handler,
)


if __name__ == "__main__":
    server.run()
