import socket
import threading
import time

import pytest


pytest.importorskip("a2a")

from a2a_wrapper import AgentCapability, AgentClient, AgentRequest, AgentServerConfig, ResponseContext, create_agent_server


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.anyio
async def test_end_to_end_echo_server():
    port = _free_port()

    async def handler(request: AgentRequest, responder: ResponseContext) -> None:
        await responder.complete(f"Echo: {request.user_text}")

    launcher = create_agent_server(
        config=AgentServerConfig(
            name="Smoke Echo Agent",
            description="Minimal smoke-test server",
            host="127.0.0.1",
            port=port,
        ),
        capabilities=[
            AgentCapability(
                capability_id="echo",
                name="Echo",
                description="Echoes text",
            )
        ],
        handler=handler,
    )

    import uvicorn

    server = uvicorn.Server(
        uvicorn.Config(launcher.get_asgi_app(), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)

    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        pytest.fail("Smoke test server did not start in time.")

    try:
        async with AgentClient(f"http://127.0.0.1:{port}") as client:
            reply = await client.send("hello smoke test")
            assert reply.text == "Echo: hello smoke test"
            assert reply.is_complete
    finally:
        server.should_exit = True
        thread.join(timeout=5)
