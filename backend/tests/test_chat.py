import asyncio

import pytest

from skill_chat.chat.service import ChatService
from skill_chat.contracts import AgentEvent, Scope, Unavailable
from skill_chat.extensions.registry import discover_extensions
from skill_chat.storage.models import turns


class QuestionGateway:
    def __init__(self, classification='{"mode":"foreground"}', answer="Answer", block=False):
        self.classification = classification
        self.answer = answer
        self.block = block
        self.executions = 0

    async def stream(self, request):
        if "intent classifier" in request.messages[0].content:
            yield AgentEvent(type="text_delta", text=self.classification)
        else:
            self.executions += 1
            yield AgentEvent(type="text_delta", text=self.answer)
            if self.block:
                await asyncio.Event().wait()
        yield AgentEvent(type="completed")

    async def cancel(self, run_id):
        pass


def service_for(repository, tmp_path, gateway):
    registry = discover_extensions(tmp_path / "skills", tmp_path / "tools")
    chat = repository.create_chat("a", "openai")
    return ChatService(repository, registry, gateway), Scope("a", chat["id"])


async def submit(service, scope):
    return await service.submit(
        scope,
        {
            "client_request_id": "one",
            "message": "Question",
            "model_id": "openai",
            "attachment_ids": [],
            "artifact_version_id": None,
        },
    )


@pytest.mark.parametrize("output", ['{"mode":[]}', '{"mode":{}}', '{"mode":"unknown"}', "not json"])
async def test_invalid_classifier_does_not_leave_a_chat_busy(repository, tmp_path, output):
    service, scope = service_for(repository, tmp_path, QuestionGateway(classification=output))
    with pytest.raises(Unavailable):
        await submit(service, scope)
    assert repository.snapshot(scope)["turns"][0]["state"] == "failed"


async def test_competing_sse_subscribers_execute_only_once(repository, tmp_path):
    gateway = QuestionGateway()
    service, scope = service_for(repository, tmp_path, gateway)
    receipt = await submit(service, scope)

    async def collect():
        return [event async for event in service.stream(scope, receipt["turn_id"])]

    first, second = await asyncio.gather(collect(), collect())
    assert gateway.executions == 1
    assert first[-1]["type"] == second[-1]["type"] == "completed"
    assert repository.get(turns, scope, receipt["turn_id"])["answer"] == "Answer"


async def test_foreground_disconnect_keeps_partial_answer_and_interrupts(repository, tmp_path):
    service, scope = service_for(repository, tmp_path, QuestionGateway(answer="Partial", block=True))
    receipt = await submit(service, scope)
    stream = service.stream(scope, receipt["turn_id"])
    assert (await anext(stream))["data"]["text"] == "Partial"
    await stream.aclose()
    saved = repository.get(turns, scope, receipt["turn_id"])
    assert saved["state"] == "interrupted"
    assert saved["answer"] == "Partial"
    assert not service.active


async def test_foreground_promotion_queues_work_without_leaking_marker(repository, tmp_path):
    service, scope = service_for(repository, tmp_path, QuestionGateway(answer="[BACKGROUND_REQUIRED]"))
    receipt = await submit(service, scope)
    assert service.claim_foreground(scope, receipt["turn_id"])
    await service.run_foreground(scope, receipt["turn_id"])
    snapshot = repository.snapshot(scope)
    assert snapshot["turns"][0]["state"] == "queued"
    assert snapshot["turns"][0]["answer"] == ""
    assert len(snapshot["tasks"]) == 1
    assert repository.read_events(scope, receipt["turn_id"])[-1]["type"] == "promoted"


async def test_foreground_deadline_is_visible_and_preserves_partial_answer(repository, tmp_path):
    repository.settings = repository.settings.model_copy(update={"foreground_timeout_seconds": 1})
    service, scope = service_for(repository, tmp_path, QuestionGateway(answer="Partial", block=True))
    receipt = await submit(service, scope)
    events = [event async for event in service.stream(scope, receipt["turn_id"])]
    assert events[-1]["type"] == "error"
    saved = repository.get(turns, scope, receipt["turn_id"])
    assert saved["state"] == "failed" and saved["answer"] == "Partial"


async def test_classifier_deadline_queues_visible_background_work(repository, tmp_path, caplog):
    from skill_chat.tasks.worker import Worker

    class SlowClassifier(QuestionGateway):
        async def stream(self, request):
            if "intent classifier" in request.messages[0].content:
                await asyncio.Event().wait()
            async for event in super().stream(request):
                yield event

    repository.settings = repository.settings.model_copy(update={"classifier_timeout_seconds": 1})
    service, scope = service_for(repository, tmp_path, SlowClassifier())
    receipt = await submit(service, scope)
    assert receipt["mode"] == "background"
    assert receipt["task_id"]
    notices = repository.read_events(scope, receipt["turn_id"])
    assert any(event["type"] == "stage" and "timed out" in event["data"]["text"] for event in notices)
    assert "timed out" in caplog.text
    worker = Worker(repository, service.registry, service.gateway)
    await worker.run_once()
    saved = repository.get(turns, scope, receipt["turn_id"])
    assert saved["state"] == "succeeded"
    assert saved["answer"] == "Answer"


@pytest.mark.parametrize("result", ["foreground", "background", "invalid", "timeout"])
async def test_cancellation_while_routing_cannot_be_resurrected(repository, tmp_path, result):
    class DelayedClassifier(QuestionGateway):
        def __init__(self):
            super().__init__()
            self.started = asyncio.Event()
            self.resume = asyncio.Event()

        async def stream(self, request):
            self.started.set()
            await self.resume.wait()
            if result == "timeout":
                raise TimeoutError
            yield AgentEvent(type="text_delta", text='{"mode":"' + result + '"}')

    gateway = DelayedClassifier()
    service, scope = service_for(repository, tmp_path, gateway)
    submission = asyncio.create_task(submit(service, scope))
    await gateway.started.wait()
    turn = repository.snapshot(scope)["turns"][0]
    await service.cancel_turn(scope, turn["id"])
    assert repository.get(turns, scope, turn["id"])["state"] == "cancelled"
    gateway.resume.set()
    from skill_chat.contracts import Conflict

    try:
        await submission
    except (Unavailable, Conflict):
        pass
    snapshot = repository.snapshot(scope)
    assert snapshot["turns"][0]["state"] == "cancelled"
    assert snapshot["tasks"] == []
