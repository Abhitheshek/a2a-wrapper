from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.tools import BaseTool

from a2a_wrapper import (
    AgentCapability,
    AgentRequest,
    AgentServerConfig,
    ResponseContext,
    create_agent_server,
)


class ResearchTool(BaseTool):
    name: str = "Research Tool"
    description: str = "Creates a structured topic summary"

    def _run(self, topic: str) -> str:
        return (
            f"Topic: {topic}\n"
            f"- Overview: short research summary\n"
            f"- Key points: major ideas and use cases\n"
            f"- Risks: important tradeoffs\n"
            f"- Next steps: areas for deeper study"
        )


def build_research_crew(topic: str) -> Crew:
    researcher = Agent(
        role="Researcher",
        goal=f"{topic} par structured research karna",
        backstory="You are a practical research analyst.",
        tools=[ResearchTool()],
        verbose=True,
        allow_delegation=False,
    )

    writer = Agent(
        role="Writer",
        goal="Research ko readable report mein convert karna",
        backstory="You write concise and useful reports.",
        verbose=True,
        allow_delegation=False,
    )

    research_task = Task(
        description=f"{topic} par research karo",
        expected_output="Structured research summary",
        agent=researcher,
    )

    writing_task = Task(
        description="Research ko final answer mein convert karo",
        expected_output="Readable final report",
        agent=writer,
        context=[research_task],
    )

    return Crew(
        agents=[researcher, writer],
        tasks=[research_task, writing_task],
        process=Process.sequential,
        verbose=True,
    )


async def crewai_handler(request: AgentRequest, responder: ResponseContext) -> None:
    await responder.progress("CrewAI team request par kaam kar rahi hai...")
    crew = build_research_crew(request.user_text)
    result = await crew.kickoff_async(inputs={"topic": request.user_text})
    await responder.complete(str(result))


server = create_agent_server(
    config=AgentServerConfig(
        name="CrewAI Research Agent",
        description="CrewAI crew exposed as an A2A server",
        host="0.0.0.0",
        port=10003,
    ),
    capabilities=[
        AgentCapability(
            capability_id="deep_research",
            name="Deep Research",
            description="Runs a CrewAI research pipeline",
            tags=["crewai", "research", "multi-agent"],
            examples=["Artificial Intelligence", "Climate change"],
        )
    ],
    handler=crewai_handler,
)


if __name__ == "__main__":
    server.run()
