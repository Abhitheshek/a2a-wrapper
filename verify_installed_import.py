from a2a_wrapper import AgentCapability, AgentClient, AgentServerConfig, create_agent_server


def main() -> None:
    capability = AgentCapability(
        capability_id="demo_capability",
        name="Demo Capability",
        description="Used to verify the published package import surface.",
    )
    config = AgentServerConfig(
        name="Demo Server",
        description="Used to verify the published package import surface.",
        host="127.0.0.1",
        port=10002,
    )

    print("IMPORT_OK")
    print(type(AgentClient).__name__)
    print(capability.name)
    print(config.base_url)
    print(callable(create_agent_server))


if __name__ == "__main__":
    main()
