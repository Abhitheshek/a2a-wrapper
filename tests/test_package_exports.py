import a2a_wrapper
import pytest


def test_package_exports_public_api_names():
    assert "AgentClient" in a2a_wrapper.__all__
    assert "AgentServerConfig" in a2a_wrapper.__all__
    assert "AgentCapability" in a2a_wrapper.__all__
    assert "ResponseContext" in a2a_wrapper.__all__
    assert "create_agent_server" in a2a_wrapper.__all__
    assert a2a_wrapper.__version__ == "0.2.0"


def test_agent_server_supports_simplified_constructor():
    pytest.importorskip("uvicorn")
    pytest.importorskip("a2a")

    async def handler(request, responder):
        await responder.complete(f"Echo: {request.user_text}")

    server = a2a_wrapper.AgentServer(
        name="Echo Agent",
        description="Simple echo agent",
        capabilities=[
            {
                "id": "echo",
                "name": "Echo",
                "description": "Echoes user input",
            }
        ],
        handler=handler,
    )

    assert server.config.name == "Echo Agent"
    assert server.config.description == "Simple echo agent"
    assert server.capabilities[0].capability_id == "echo"
    assert server.capabilities[0].name == "Echo"


def test_agent_server_auto_creates_default_capability():
    pytest.importorskip("uvicorn")
    pytest.importorskip("a2a")

    async def handler(request, responder):
        await responder.complete("done")

    server = a2a_wrapper.AgentServer(
        name="Support Agent",
        description="Handles support questions",
        handler=handler,
    )

    assert server.capabilities[0].capability_id == "support-agent"
    assert server.capabilities[0].name == "Support Agent"
    assert server.capabilities[0].description == "Handles support questions"


def test_agent_server_auto_fills_missing_capability_fields():
    pytest.importorskip("uvicorn")
    pytest.importorskip("a2a")

    async def handler(request, responder):
        await responder.complete("done")

    server = a2a_wrapper.AgentServer(
        name="Research Agent",
        description="Runs research tasks",
        capabilities=[{"id": "research"}],
        handler=handler,
    )

    assert server.capabilities[0].capability_id == "research"
    assert server.capabilities[0].name == "Research Agent"
    assert server.capabilities[0].description == "Runs research tasks"


def test_agent_server_capability_helper_creates_capability():
    capability = a2a_wrapper.AgentServer.capability(
        "summarize",
        "Summarize",
        "Summarizes long text",
        tags=["text"],
    )

    assert capability.capability_id == "summarize"
    assert capability.name == "Summarize"
    assert capability.tags == ["text"]
