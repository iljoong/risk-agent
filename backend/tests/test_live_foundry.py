import os
from uuid import uuid4

import pytest

from skill_chat.agents.gateway import AgentGateway
from skill_chat.config import load_settings
from skill_chat.contracts import AgentRequest, ContextMessage, Scope


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("APP_RUN_LIVE_TESTS") != "1",
    reason="Set APP_RUN_LIVE_TESTS=1 to use real configured Foundry resources",
)
async def test_both_configured_foundry_providers_stream_with_azure_identity():
    settings = load_settings()
    gateway = AgentGateway(settings)
    try:
        for provider in ("openai", "anthropic"):
            model = next((model for model in settings.models if model.provider == provider), None)
            assert model is not None, f"Configure at least one {provider} model for live verification"
            output = [
                event
                async for event in gateway.stream(
                    AgentRequest(
                        uuid4().hex,
                        Scope("live-test", uuid4().hex),
                        model.id,
                        (ContextMessage(role="user", content="Reply with a brief greeting."),),
                        allow_tools=False,
                    )
                )
            ]
            assert any(event.type == "text_delta" and event.text.strip() for event in output)
    finally:
        await gateway.close()


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("APP_RUN_LIVE_TESTS") != "1" or os.environ.get("APP_RUN_LIVE_SKILL_TESTS") != "1",
    reason="Live RFP generation requires both explicit live-test opt-ins",
)
async def test_live_rfp_skill_publishes_page_referenced_evidence_aware_slides(tmp_path):
    from test_documents import make_pdf

    from skill_chat.documents.ingestion import AttachmentService
    from skill_chat.extensions.registry import build_registry
    from skill_chat.storage.repository import Repository
    from skill_chat.tasks.service import TaskService
    from skill_chat.tasks.worker import Worker

    configured = load_settings()
    settings = configured.model_copy(
        update={
            "data_dir": tmp_path,
            "background_timeout_seconds": min(configured.background_timeout_seconds, 180),
        }
    )
    repository = Repository(settings)
    registry = build_registry(repository)
    gateway = AgentGateway(settings, registry)
    chat = repository.create_chat("live-test", settings.default_model_id)
    scope = Scope("live-test", chat["id"])
    attachment = AttachmentService(repository).upload(scope, "RFP.pdf", make_pdf())
    turn, _ = repository.create_turn(
        scope,
        {
            "client_request_id": uuid4().hex,
            "message": "Draft RFP response slides. We have not supplied any supplier evidence.",
            "model_id": settings.default_model_id,
            "skill_id": "rfp-response",
            "attachment_ids": [attachment["id"]],
        },
    )
    tasks = TaskService(repository)
    task = tasks.enqueue(scope, turn["id"], settings.default_model_id, "rfp-response", registry.fingerprint)
    try:
        await Worker(repository, registry, gateway).run_once()
        result = tasks.get(scope, task["id"])
        assert result["state"] == "succeeded", result["error"]
        artifacts = repository.snapshot(scope)["artifacts"]
        assert artifacts
        assert "Needs confirmation" in artifacts[-1]["text_content"]
        assert "RFP.pdf, page 1" in artifacts[-1]["text_content"]
    finally:
        await gateway.close()
        repository.db.engine.dispose()
