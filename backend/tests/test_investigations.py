import pytest

from skill_chat.contracts import Conflict, InvalidInput, NotFound, Scope


def create_investigation(repository):
    from skill_chat.investigations.service import InvestigationService

    service = InvestigationService(repository)
    receipt = service.create("a", "openai", "create-demo")
    return service, Scope("a", receipt["chat_id"])


def command(service, scope, action, payload, request_id="action"):
    from skill_chat.investigations.schemas import InvestigationCommand

    return service.apply(scope, InvestigationCommand(
        client_request_id=request_id,
        expected_revision=service.get(scope)["revision"],
        action=action,
        payload=payload,
    ))


def test_investigation_commands_are_scoped_idempotent_and_version_checked(repository):
    from skill_chat.investigations.schemas import InvestigationCommand

    service, scope = create_investigation(repository)
    assert service.create("a", "openai", "create-demo")["chat_id"] == scope.chat_id
    amendment = InvestigationCommand(
        client_request_id="edit", expected_revision=1, action="amend_output",
        payload={"stage_id": "investigate", "text": "Assess only the permitted sources.", "reason": "Narrow scope"},
    )
    receipt = service.apply(scope, amendment)
    assert service.apply(scope, amendment) == receipt
    assert service.get(scope)["revision"] == 2
    with pytest.raises(Conflict):
        service.apply(scope, amendment.model_copy(update={"payload": {**amendment.payload, "text": "Different"}}))
    with pytest.raises(Conflict):
        service.apply(scope, amendment.model_copy(update={"client_request_id": "stale"}))
    with pytest.raises(NotFound):
        service.get(Scope("b", scope.chat_id))
    other = service.create("a", "openai", "other-demo")
    assert service.get(Scope("a", other["chat_id"]))["revision"] == 1


def test_amendments_preserve_history_and_invalidate_dependent_review(repository):
    service, scope = create_investigation(repository)
    before = service.get(scope)["outputs"]["investigate"]["text"]
    command(service, scope, "amend_output", {
        "stage_id": "investigate", "text": "Beneficiary not observed in available history.", "reason": "Avoid overclaiming",
    })
    state = service.get(scope)
    assert state["outputs"]["analyze"]["needs_review"]
    assert state["history"][-1]["before"] == before
    assert state["history"][-1]["after"] == "Beneficiary not observed in available history."
    assert state["original_alert"]["priority"] == "High"
    with pytest.raises(Conflict):
        command(service, scope, "review_note", {"rationale": "Review with open gaps"})
    with pytest.raises(InvalidInput):
        command(service, scope, "amend_output", {"stage_id": "analyze", "text": "Changed", "reason": " "}, "bad")


def test_shared_fact_change_invalidates_review_and_prepared_note(repository):
    from skill_chat.investigations.schemas import STAGES

    service, scope = create_investigation(repository)
    for index, stage in enumerate(STAGES):
        command(service, scope, "acknowledge_stage", {"stage_id": stage}, f"ack-{index}")
    command(service, scope, "review_note", {"rationale": "Both material gaps remain acknowledged."}, "review")
    command(service, scope, "prepare_note", {}, "export")
    assert "unconfirmed" in service.get(scope)["review"]["prepared_note"].lower()
    command(service, scope, "amend_fact", {
        "beneficiary_description": "Not observed in the available 90-day history", "reason": "Qualify coverage",
    }, "fact")
    state = service.get(scope)
    assert not state["review"]["reviewed"]
    assert state["review"]["prepared_note"] is None
    assert all(item["needs_review"] for item in state["outputs"].values())
    with pytest.raises(Conflict):
        command(service, scope, "prepare_note", {}, "not-reviewed")
