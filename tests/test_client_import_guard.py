import pytest

from a2a_wrapper import _client as client_module


def test_client_raises_helpful_error_when_sdk_missing(monkeypatch):
    monkeypatch.setattr(client_module, "_IMPORT_ERROR", ModuleNotFoundError("a2a"))

    with pytest.raises(RuntimeError, match="a2a-sdk is required"):
        client_module.A2AAgentClient("http://localhost:10002")
