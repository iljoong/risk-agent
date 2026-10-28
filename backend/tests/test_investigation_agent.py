import pytest
from test_investigation_connector import NoInference, prepare
from test_investigations import command, create_investigation

from skill_chat.chat.service import ChatService
from skill_chat.contracts import AgentEvent, Conflict, InvalidInput, NotFound, Scope, Unavailable
from skill_chat.extensions.registry import build_registry
from skill_chat.investigations.schemas import InvestigationCommand
from skill_chat.storage.models import turns
from skill_chat.tasks.worker import Worker
from skill_chat.tools.context import ToolContext


async def setup_prepared(repository):
    service, scope = create_investigation(repository)
    registry = build_registry(repository)
    prepare(service, scope, registry)
    await Worker(repository, registry, NoInference()).run_once()
    return service, scope, registry


class UpdatingGateway:
    def __init__(self, repository, fail=False):
        self.repo = repository
        self.fail = fail

    async def stream(self, request):
        assert any("ANALYST AMENDED SCOPE" in message.content for message in request.messages)
        from skill_chat.tools.investigations import investigation_tools

        tool = next(tool for tool in investigation_tools(self.repo) if tool.name == "propose_investigation_output")
        revision = self.repo.get(turns, request.scope, request.run_id)["request"]["investigation"]["base_revision"]
        await tool.handler(tool.arguments.model_validate({
            "expected_revision": revision, "stage_id": "analyze",
            "text": "Supplier activity is plausible, but this invoice is unverified [E-03, GAP-01].",
            "evidence_ids": ["E-03", "GAP-01"],
        }), ToolContext(request.scope, request.run_id, request.task_id))
        if self.fail:
            yield AgentEvent(type="error", text="Provider failed after proposing output")
        else:
            yield AgentEvent(type="text_delta", text="Analysis updated with counterevidence.")
            yield AgentEvent(type="completed")

    async def cancel(self, run_id):
        pass


@pytest.mark.parametrize("fail", [False, True])
async def test_amended_context_and_success_only_agent_publication(repository, fail):
    service, scope, registry = await setup_prepared(repository)
    command(service, scope, "amend_output", {
        "stage_id": "investigate", "text": "ANALYST AMENDED SCOPE", "reason": "Narrow checks",
    })
    previous = service.get(scope)["outputs"]["analyze"]["text"]
    gateway = UpdatingGateway(repository, fail=fail)
    chat = ChatService(repository, registry, gateway)
    body = {"client_request_id": "challenge", "message": "Challenge this concern and update analysis.",
            "model_id": "openai", "attachment_ids": [], "skill_id": None, "artifact_version_id": None}
    receipt = await chat.submit(scope, body)
    assert receipt["mode"] == "background"
    await Worker(repository, registry, gateway).run_once()
    output = service.get(scope)["outputs"]["analyze"]["text"]
    assert (output == previous) is fail
    assert repository.get(turns, scope, receipt["turn_id"])["state"] == ("failed" if fail else "succeeded")
    assert (await chat.submit(scope, body))["turn_id"] == receipt["turn_id"]


async def test_investigation_reader_and_updates_are_scoped_bounded_and_revision_checked(repository):
    from skill_chat.tools.investigations import investigation_tools

    service, scope, registry = await setup_prepared(repository)
    tools = {tool.name: tool for tool in investigation_tools(repository)}
    reader = tools["read_investigation"]
    result = await reader.handler(reader.arguments.model_validate({}), ToolContext(scope, "read", None))
    assert len(result) < 4000
    with pytest.raises(NotFound):
        await reader.handler(reader.arguments.model_validate({}), ToolContext(Scope("b", scope.chat_id), "read", None))
    proposal = tools["propose_investigation_output"]
    with pytest.raises(InvalidInput):
        await proposal.handler(proposal.arguments.model_validate({
            "stage_id": "analyze", "expected_revision": 1, "text": "Unsupported claim",
            "evidence_ids": ["FAKE-SOURCE"],
        }), ToolContext(scope, "read", None))
    receipt = await ChatService(repository, registry, NoInference()).submit(scope, {
        "client_request_id": "pending", "message": "Investigate",
        "model_id": "openai", "attachment_ids": [], "skill_id": None, "artifact_version_id": None,
    })
    with pytest.raises(Conflict):
        service.apply(scope, InvestigationCommand(
            client_request_id="busy", expected_revision=service.get(scope)["revision"], action="select_stage",
            payload={"stage_id": "detect"},
        ))
    assert receipt["task_id"]


def test_investigation_context_never_silently_truncates_amendments(repository):
    from skill_chat.investigations.context import build_investigation_context

    service, scope = create_investigation(repository)
    state = service.get(scope)
    state["outputs"]["investigate"]["text"] = "Very long scope " * 1000
    with pytest.raises(Unavailable, match="context"):
        build_investigation_context(state, 200)


async def test_resolved_scope_runs_without_spending_context_on_renderer_operations(repository):
    service, scope, registry = await setup_prepared(repository)
    command(service, scope, "amend_output", {
        "stage_id": "investigate", "text": "ANALYST AMENDED SCOPE", "reason": "Narrow checks",
    })
    command(service, scope, "request_clarification", {}, "ask")
    pending = service.get(scope)["clarification"]
    receipt = service.apply(scope, InvestigationCommand(
        client_request_id="resolve", expected_revision=service.get(scope)["revision"], action="resolve_clarification",
        payload={"clarification_id": pending["id"], "surface_revision": pending["surface_revision"],
                 "answer": "Compare the supplier explanation, retaining the invoice gap."},
    ), registry_fingerprint=registry.fingerprint)
    await Worker(repository, registry, UpdatingGateway(repository)).run_once()
    turn = repository.get(turns, scope, receipt["turn_id"])
    assert turn["state"] == "succeeded", turn["error"]
