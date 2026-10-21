import time

import pytest
from sqlalchemy import update

from skill_chat.artifacts.service import ArtifactService
from skill_chat.contracts import Conflict, NotFound, Scope
from skill_chat.storage.models import tasks, turns
from skill_chat.tasks.service import TaskService


def setup_task(repository):
    chat = repository.create_chat("a", "openai")
    scope = Scope("a", chat["id"])
    turn, _ = repository.create_turn(
        scope,
        {
            "client_request_id": "1",
            "message": "draft",
            "model_id": "openai",
            "attachment_ids": [],
        },
    )
    service = TaskService(repository)
    task = service.enqueue(scope, turn["id"], "openai", None, "registry")
    return scope, turn, task, service


def test_competing_claims_cancel_and_terminal_state(repository):
    scope, turn, task, service = setup_task(repository)
    assert service.claim_next("w1")["id"] == task["id"]
    assert service.claim_next("w2") is None
    service.request_cancel(scope, task["id"])
    service.finish(scope, task["id"], "succeeded", "This must not be success")
    assert service.get(scope, task["id"])["state"] == "cancelled"
    assert repository.get(turns, scope, turn["id"])["state"] == "cancelled"
    with pytest.raises(NotFound):
        service.get(Scope("b", scope.chat_id), task["id"])


def test_expired_running_lease_is_not_automatically_replayed(repository):
    scope, _, task, service = setup_task(repository)
    service.claim_next("dead")
    with repository.db.transaction() as connection:
        connection.execute(update(tasks).where(tasks.c.id == task["id"]).values(heartbeat=time.time() - 100))
    assert service.recover_expired() == 1
    assert service.get(scope, task["id"])["state"] == "interrupted"
    assert service.claim_next("replacement") is None
    retried = service.retry(scope, task["id"], "registry")
    assert retried["retry_of"] == task["id"]


def test_artifacts_are_hidden_until_success_and_cancel_cannot_publish(repository):
    scope, turn, task, service = setup_task(repository)
    service.claim_next("w1")
    artifacts = ArtifactService(repository)
    draft = artifacts.publish(scope, turn["id"], task["id"], "<section><h1>Draft</h1></section>", "Draft")
    with pytest.raises(NotFound):
        artifacts.get(scope, draft["id"])
    service.finish(scope, task["id"], "succeeded", "Done")
    assert artifacts.get(scope, draft["id"])["version"] == 1
    with pytest.raises(Conflict):
        artifacts.publish(scope, turn["id"], task["id"], "<p>Too late</p>", "Late")


def test_duplicate_turn_is_idempotent_and_changed_payload_conflicts(repository):
    scope, turn, _, _ = setup_task(repository)
    repeat, created = repository.create_turn(scope, turn["request"])
    assert not created and repeat["id"] == turn["id"]
    with pytest.raises(Conflict):
        repository.create_turn(scope, {**turn["request"], "message": "different"})


def test_interrupted_background_work_retains_partial_answer(repository):
    scope, turn, task, service = setup_task(repository)
    service.claim_next("dead")
    repository.change(turns, scope, turn["id"], answer="Partial task answer")
    with repository.db.transaction() as connection:
        connection.execute(update(tasks).where(tasks.c.id == task["id"]).values(heartbeat=time.time() - 100))
    service.recover_expired()
    assert repository.get(turns, scope, turn["id"])["answer"] == "Partial task answer"


def test_failed_background_work_retains_partial_answer(repository):
    scope, turn, task, service = setup_task(repository)
    service.claim_next("worker")
    repository.change(turns, scope, turn["id"], answer="Partial task answer")
    service.finish(scope, task["id"], "failed", error="Provider request failed")
    assert repository.get(turns, scope, turn["id"])["answer"] == "Partial task answer"


def test_artifact_revision_keeps_original_version_immutable_and_owner_scoped(repository):
    scope, turn, task, service = setup_task(repository)
    service.claim_next("worker")
    artifacts = ArtifactService(repository)
    original = artifacts.publish(scope, turn["id"], task["id"], "<p>Original draft</p>", "Draft")
    service.finish(scope, task["id"], "succeeded", "Saved")
    revision_turn, _ = repository.create_turn(
        scope,
        {
            **turn["request"],
            "client_request_id": "revision",
            "artifact_version_id": original["id"],
        },
    )
    revision_task = service.enqueue(scope, revision_turn["id"], "openai", None, "registry")
    service.claim_next("worker")
    revision = artifacts.publish(
        scope, revision_turn["id"], revision_task["id"], "<p>Revised draft</p>", "Draft", original["id"]
    )
    service.finish(scope, revision_task["id"], "succeeded", "Revised")
    assert artifacts.read_html(scope, original["id"]) == "<p>Original draft</p>"
    assert artifacts.get(scope, revision["id"])["version"] == 2
    assert artifacts.get(scope, revision["id"])["parent_version_id"] == original["id"]
    with pytest.raises(NotFound):
        artifacts.get(Scope("b", scope.chat_id), revision["id"])
