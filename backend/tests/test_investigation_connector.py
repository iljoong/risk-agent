import asyncio

import pytest
from test_investigations import create_investigation

from skill_chat.contracts import Conflict, Scope
from skill_chat.extensions.registry import build_registry
from skill_chat.investigations.schemas import InvestigationCommand
from skill_chat.storage.models import investigation_candidates, turns
from skill_chat.tasks.service import TaskService
from skill_chat.tasks.worker import Worker


class NoInference:
    async def stream(self, request):
        raise AssertionError("Demo connector preparation must not call a model")
        yield

    async def cancel(self, run_id):
        pass


def prepare(service, scope, registry):
    return service.prepare(scope, InvestigationCommand(
        client_request_id="prepare", expected_revision=service.get(scope)["revision"],
        action="prepare", payload={},
    ), registry.fingerprint)


async def test_demo_preparation_publishes_calculations_and_preserves_gaps(repository):
    service, scope = create_investigation(repository)
    registry = build_registry(repository)
    receipt = prepare(service, scope, registry)
    await Worker(repository, registry, NoInference()).run_once()
    state = service.get(scope)
    assert state["prepared"]
    assert state["calculations"] == {
        "incoming_gbp": 48000, "outgoing_gbp": 45500, "ratio_percent": "94.79", "elapsed_minutes": 56,
    }
    results = {source["source_id"]: source for source in state["sources"]}
    assert results["SRC-04"]["status"] == "restricted"
    assert results["SRC-07"]["status"] == "missing"
    assert results["SRC-01"]["retrieved_at"] != results["SRC-01"]["snapshot_at"]
    assert "fund lineage" in state["outputs"]["analyze"]["text"]
    assert repository.get(turns, scope, receipt["turn_id"])["state"] == "succeeded"


async def test_alert_without_demo_records_prepares_an_explicit_source_gap(repository):
    from skill_chat.investigations.service import InvestigationService

    service = InvestigationService(repository)
    opened = service.open_alert("a", "openai", "ALT-2036", "open-quayside")
    scope = Scope("a", opened["chat_id"])
    registry = build_registry(repository)
    prepare(service, scope, registry)
    await Worker(repository, registry, NoInference()).run_once()
    state = service.get(scope)
    assert state["prepared"] and not state["transactions"]
    assert [source["status"] for source in state["sources"]] == ["missing"]
    assert state["evidence"][0]["kind"] == "Missing information"
    assert "No finding can be drawn" in state["outputs"]["analyze"]["text"]


async def test_preparation_is_idempotent_and_blocks_conflicting_edits(repository):
    service, scope = create_investigation(repository)
    registry = build_registry(repository)
    cmd = InvestigationCommand(client_request_id="prepare", expected_revision=1, action="prepare")
    receipt = service.prepare(scope, cmd, registry.fingerprint)
    assert service.prepare(scope, cmd, registry.fingerprint) == receipt
    with pytest.raises(Conflict):
        service.apply(scope, InvestigationCommand(
            client_request_id="edit", expected_revision=2, action="amend_fact",
            payload={"beneficiary_description": "Changed", "reason": "While busy"},
        ))
    await Worker(repository, registry, NoInference()).run_once()
    other = service.create("a", "openai", "second-session")
    assert not service.get(Scope("a", other["chat_id"]))["prepared"]


async def test_cancelled_connector_keeps_partial_outcomes_without_publishing(repository):
    from skill_chat.investigations.connector import DemoInvestigationConnector

    class PausingConnector(DemoInvestigationConnector):
        async def retrieve(self, source_id):
            if source_id == "SRC-02":
                await asyncio.sleep(10)
            return await super().retrieve(source_id)

    service, scope = create_investigation(repository)
    registry = build_registry(repository)
    receipt = prepare(service, scope, registry)
    worker = Worker(repository, registry, NoInference(), connector=PausingConnector())
    job = asyncio.create_task(worker.run_once())
    for _ in range(100):
        candidates = repository.list_records(investigation_candidates, scope)
        if candidates and candidates[0]["payload"].get("sources"):
            break
        await asyncio.sleep(0.01)
    TaskService(repository).request_cancel(scope, receipt["task_id"])
    await job
    assert not service.get(scope)["prepared"]
    assert repository.list_records(investigation_candidates, scope)[0]["payload"]["sources"][0]["source_id"] == "SRC-01"
    assert repository.get(turns, scope, receipt["turn_id"])["state"] == "cancelled"
    retry = TaskService(repository).retry(scope, receipt["task_id"], registry.fingerprint)
    await Worker(repository, registry, NoInference()).run_once()
    assert TaskService(repository).get(scope, retry["id"])["state"] == "succeeded"
