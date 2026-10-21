from test_documents import make_pdf

from skill_chat.artifacts.service import ArtifactService
from skill_chat.contracts import AgentEvent, Scope
from skill_chat.documents.ingestion import AttachmentService
from skill_chat.extensions.registry import discover_extensions
from skill_chat.storage.models import turns
from skill_chat.tasks.service import TaskService
from skill_chat.tasks.worker import Worker


class DraftGateway:
    def __init__(self, repo):
        self.repo = repo

    async def stream(self, request):
        assert request.scope.owner_id == "a"
        assert any("RFP.pdf, page 1" in message.content for message in request.messages)
        ArtifactService(self.repo).publish(
            request.scope,
            request.run_id,
            request.task_id,
            "<section><h1>Draft</h1><p>Needs confirmation</p><p>RFP.pdf, page 1</p></section>",
            "Draft",
        )
        yield AgentEvent(type="text_delta", text="Draft saved. Needs confirmation: supplier evidence.")
        yield AgentEvent(type="completed")

    async def cancel(self, run_id):
        pass


async def test_worker_ingests_pdf_and_publishes_only_complete_artifact(repository, settings, tmp_path):
    registry = discover_extensions(tmp_path / "skills", tmp_path / "tools")
    chat = repository.create_chat("a", "openai")
    scope = Scope("a", chat["id"])
    attachment = AttachmentService(repository).upload(scope, "RFP.pdf", make_pdf())
    turn, _ = repository.create_turn(
        scope,
        {
            "client_request_id": "1",
            "message": "Make slides",
            "model_id": "openai",
            "attachment_ids": [attachment["id"]],
            "artifact_version_id": None,
        },
    )
    service = TaskService(repository)
    task = service.enqueue(scope, turn["id"], "openai", None, registry.fingerprint)
    worker = Worker(repository, registry, DraftGateway(repository))
    assert await worker.run_once()
    assert service.get(scope, task["id"])["state"] == "succeeded"
    snapshot = repository.snapshot(scope)
    assert len(snapshot["artifacts"]) == 1
    assert "Needs confirmation" in snapshot["artifacts"][0]["text_content"]


async def test_registry_change_does_not_run_old_job(repository, settings, tmp_path):
    registry = discover_extensions(tmp_path / "skills", tmp_path / "tools")
    chat = repository.create_chat("a", "openai")
    scope = Scope("a", chat["id"])
    turn, _ = repository.create_turn(
        scope,
        {
            "client_request_id": "1",
            "message": "Make slides",
            "model_id": "openai",
            "attachment_ids": [],
        },
    )
    service = TaskService(repository)
    task = service.enqueue(scope, turn["id"], "openai", None, "obsolete")
    await Worker(repository, registry, DraftGateway(repository)).run_once()
    assert service.get(scope, task["id"])["state"] == "failed"
    assert "Extensions changed" in repository.get(turns, scope, turn["id"])["error"]


async def test_rfp_skill_requires_a_processed_pdf_before_inference(repository):
    from test_chat import QuestionGateway

    from skill_chat.extensions.registry import build_registry

    registry = build_registry(repository)
    chat = repository.create_chat("a", "openai")
    scope = Scope("a", chat["id"])
    turn, _ = repository.create_turn(
        scope,
        {
            "client_request_id": "no-pdf",
            "message": "Draft slides",
            "model_id": "openai",
            "skill_id": "rfp-response",
            "attachment_ids": [],
        },
    )
    tasks = TaskService(repository)
    task = tasks.enqueue(scope, turn["id"], "openai", "rfp-response", registry.fingerprint)
    gateway = QuestionGateway()
    await Worker(repository, registry, gateway).run_once()
    assert "Attach at least one" in tasks.get(scope, task["id"])["error"]
    assert gateway.executions == 0
