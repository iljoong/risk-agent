import json

import pytest
from test_config import models

from skill_chat.agents.gateway import assert_sdk_compatibility, build_provider
from skill_chat.config import load_settings


async def test_provider_refreshes_credentials_for_both_protocols(tmp_path):
    settings = load_settings({"APP_MODELS": json.dumps(models()), "APP_DATA_DIR": str(tmp_path)})
    count = 0

    async def token():
        nonlocal count
        count += 1
        return f"fresh-{count}"

    for model in settings.models:
        provider = build_provider(model, token)
        assert "api_key" not in provider
        assert "bearer_token" not in provider
        callback = provider["bearer_token_provider"]
        assert await callback({}) != await callback({})
        assert provider["type"] == model.provider
    assert_sdk_compatibility()


def test_sdk_incompatibility_fails_explicitly():
    with pytest.raises(RuntimeError, match="bearer_token_provider"):
        assert_sdk_compatibility(provider_fields={})


async def test_gateway_converts_messages_and_filters_reasoning(settings, monkeypatch):
    from agent_framework import AgentResponseUpdate, Content

    from skill_chat.agents.gateway import AgentGateway
    from skill_chat.contracts import AgentRequest, ContextMessage, Scope

    class ProviderBoundary:
        def __init__(self, **kwargs):
            from copilot.generated.rpc import PermissionDecisionReject
            from copilot.generated.session_events import PermissionRequestCustomTool, PermissionRequestRead

            permission = kwargs["default_options"]["on_permission_request"]
            assert isinstance(
                permission(PermissionRequestCustomTool(tool_description="Unknown", tool_name="shell"), {}),
                PermissionDecisionReject,
            )
            assert isinstance(
                permission(PermissionRequestRead(intention="Read", path=str(settings.project_dir)), {}),
                PermissionDecisionReject,
            )

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def run(self, messages, stream):
            assert messages[-1].text == "Hello"
            yield AgentResponseUpdate(
                contents=[Content.from_text("Public answer"), Content.from_text_reasoning(text="Private")]
            )

    monkeypatch.setattr("skill_chat.agents.gateway.GitHubCopilotAgent", ProviderBoundary)
    gateway = AgentGateway(settings)
    try:
        output = [
            event
            async for event in gateway.stream(
                AgentRequest(
                    "run1",
                    Scope("a", "chat1"),
                    "openai",
                    (ContextMessage(role="user", content="Hello"),),
                )
            )
        ]
        assert "".join(event.text for event in output) == "Public answer"
    finally:
        await gateway.close()


@pytest.mark.parametrize("kind", ["agent", "azure"])
async def test_provider_failures_are_visible_without_leaking_provider_details(settings, monkeypatch, kind):
    from agent_framework.exceptions import AgentInvalidAuthException
    from azure.core.exceptions import ClientAuthenticationError

    from skill_chat.agents.gateway import AgentGateway
    from skill_chat.contracts import AgentRequest, ContextMessage, Scope, Unavailable

    class FailingProvider:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            error = AgentInvalidAuthException if kind == "agent" else ClientAuthenticationError
            raise error("private-provider-detail")

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr("skill_chat.agents.gateway.GitHubCopilotAgent", FailingProvider)
    gateway = AgentGateway(settings)
    try:
        with pytest.raises(Unavailable, match="Provider request failed") as failure:
            _ = [
                event
                async for event in gateway.stream(
                    AgentRequest(
                        "run1",
                        Scope("a", "chat1"),
                        "openai",
                        (ContextMessage(role="user", content="Hello"),),
                    )
                )
            ]
        assert "private-provider-detail" not in str(failure.value)
        assert not gateway.active
    finally:
        await gateway.close()
