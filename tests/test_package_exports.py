import a2a_wrapper


def test_package_exports_public_api_names():
    assert "AgentClient" in a2a_wrapper.__all__
    assert "AgentServerConfig" in a2a_wrapper.__all__
    assert "AgentCapability" in a2a_wrapper.__all__
    assert "ResponseContext" in a2a_wrapper.__all__
    assert "create_agent_server" in a2a_wrapper.__all__
    assert a2a_wrapper.__version__ == "0.2.0"
