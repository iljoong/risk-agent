import copy

import pytest
from test_investigations import create_investigation

from skill_chat.contracts import Conflict, InvalidInput
from skill_chat.investigations.schemas import InvestigationCommand


def action(service, scope, name, payload, request_id):
    return InvestigationCommand(
        action=name, payload=payload, client_request_id=request_id,
        expected_revision=service.get(scope)["revision"],
    )


def test_clarification_resolution_is_persistent_and_queues_exactly_one_turn(repository):
    from skill_chat.investigations.projection import InvestigationProjection

    service, scope = create_investigation(repository)
    service.apply(scope, action(service, scope, "request_clarification", {}, "ask"))
    pending = service.get(scope)["clarification"]
    assert pending["status"] == "pending"
    assert repository.snapshot(scope)["tasks"] == []
    frames = InvestigationProjection(repository).read_ui_events(scope, 0)
    activity = frames[-1]["payload"]
    assert activity["type"] == "ACTIVITY_SNAPSHOT"
    assert activity["activityType"] == "a2ui-surface"
    assert activity["content"]["a2ui_operations"] == pending["operations"]
    resolve = action(service, scope, "resolve_clarification", {
        "clarification_id": pending["id"], "surface_revision": pending["surface_revision"],
        "answer": "Compare the supplier explanation without inferring wrongdoing.",
    }, "answer")
    receipt = service.apply(scope, resolve, registry_fingerprint="test")
    assert service.apply(scope, resolve, registry_fingerprint="test") == receipt
    state = service.get(scope)
    assert state["clarification"]["status"] == "resolved"
    snapshot = repository.snapshot(scope)
    assert len(snapshot["turns"]) == len(snapshot["tasks"]) == 1
    assert snapshot["turns"][0]["request"]["investigation"]["snapshot"]["clarification"]["answer"] == resolve.payload["answer"]
    with pytest.raises(Conflict):
        service.apply(scope, action(service, scope, "resolve_clarification", resolve.payload, "another"), registry_fingerprint="test")


def test_cancel_foreign_stale_and_oversized_clarifications(repository):
    service, scope = create_investigation(repository)
    service.apply(scope, action(service, scope, "request_clarification", {}, "ask"))
    pending = service.get(scope)["clarification"]
    with pytest.raises(Conflict):
        service.apply(scope, action(service, scope, "request_clarification", {}, "second"))
    body = {"clarification_id": pending["id"], "surface_revision": pending["surface_revision"], "answer": "Scope"}
    for bad in [{**body, "clarification_id": "foreign"}, {**body, "surface_revision": 999}]:
        with pytest.raises(Conflict):
            service.apply(scope, action(service, scope, "resolve_clarification", bad, "invalid"), registry_fingerprint="test")
    with pytest.raises(InvalidInput):
        service.apply(scope, action(service, scope, "resolve_clarification", {**body, "answer": "界" * 6000}, "large"), registry_fingerprint="test")
    service.apply(scope, action(service, scope, "cancel_clarification", {
        "clarification_id": pending["id"], "surface_revision": pending["surface_revision"],
    }, "cancel"))
    with pytest.raises(Conflict):
        service.apply(scope, action(service, scope, "resolve_clarification", body, "late"), registry_fingerprint="test")
    assert repository.snapshot(scope)["tasks"] == []


def test_only_the_bounded_scope_surface_catalog_is_accepted():
    from skill_chat.investigations.surfaces import build_scope_surface, validate_scope_surface

    operations = build_scope_surface("clarify-1", 1, "Narrow the scope.")
    validate_scope_surface(operations)
    bad = copy.deepcopy(operations)
    bad[1]["updateComponents"]["components"][0]["component"] = "Video"
    with pytest.raises(InvalidInput):
        validate_scope_surface(bad)
    for malformed in [
        [{"script": "not permitted"}],
        [{"x": "x" * 65537}],
        operations + operations,
    ]:
        with pytest.raises(InvalidInput):
            validate_scope_surface(malformed)


def test_resolution_rolls_back_if_task_enqueue_fails(repository, monkeypatch):
    from skill_chat.tasks.service import TaskService

    service, scope = create_investigation(repository)
    service.apply(scope, action(service, scope, "request_clarification", {}, "ask"))
    pending = service.get(scope)["clarification"]
    resolve = action(service, scope, "resolve_clarification", {
        "clarification_id": pending["id"], "surface_revision": pending["surface_revision"], "answer": "Permitted scope",
    }, "answer")
    def fail(*args, **kwargs):
        raise Conflict("Queue unavailable")
    monkeypatch.setattr(TaskService, "enqueue", fail)
    with pytest.raises(Conflict):
        service.apply(scope, resolve, registry_fingerprint="test")
    assert service.get(scope)["clarification"]["status"] == "pending"
    assert repository.snapshot(scope)["turns"] == []
