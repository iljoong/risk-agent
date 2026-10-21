import asyncio
import subprocess
import sys
import time
from pathlib import Path

from e2e_server import TestProvider as DeterministicProvider
from sqlalchemy import update

from skill_chat.contracts import Scope
from skill_chat.extensions.registry import build_registry
from skill_chat.storage.models import tasks
from skill_chat.storage.repository import Repository
from skill_chat.tasks.service import TaskService
from skill_chat.tasks.worker import Worker


async def test_worker_termination_does_not_replay_running_work_or_lose_queue(repository, settings, tmp_path):
    registry = build_registry(repository)
    service = TaskService(repository)
    queued = []
    for number in range(2):
        chat = repository.create_chat("local", "openai")
        scope = Scope("local", chat["id"])
        turn, _ = repository.create_turn(
            scope,
            {
                "client_request_id": str(number),
                "message": "Generate slides",
                "model_id": "openai",
                "attachment_ids": [],
            },
        )
        task = service.enqueue(scope, turn["id"], "openai", None, registry.fingerprint)
        queued.append((scope, task))
    log_path = tmp_path / "worker-output.log"
    with log_path.open("w+", encoding="utf-8") as log:
        process = await asyncio.to_thread(
            subprocess.Popen,
            [
                sys.executable,
                str(Path(__file__).with_name("e2e_server.py")),
                "worker",
                str(settings.data_dir),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            scope, first = queued[0]
            deadline = time.monotonic() + 15
            while service.get(scope, first["id"])["state"] == "queued" and time.monotonic() < deadline:
                assert process.poll() is None, "Test worker exited before claiming work"
                await asyncio.sleep(0.03)
            assert service.get(scope, first["id"])["state"] == "running"
            process.terminate()
            await asyncio.to_thread(process.wait, timeout=5)
        finally:
            if process.poll() is None:
                process.kill()
                await asyncio.to_thread(process.wait, timeout=5)
    reopened = Repository(settings)
    recovered = TaskService(reopened)
    with reopened.db.transaction() as connection:
        connection.execute(update(tasks).where(tasks.c.id == first["id"]).values(heartbeat=time.time() - 100))
    assert recovered.recover_expired() == 1
    assert recovered.get(scope, first["id"])["state"] == "interrupted"
    other_scope, second = queued[1]
    assert recovered.get(other_scope, second["id"])["state"] == "queued"
    await Worker(reopened, build_registry(reopened), DeterministicProvider(reopened)).run_once()
    assert recovered.get(other_scope, second["id"])["state"] == "succeeded"
    assert recovered.get(scope, first["id"])["state"] == "interrupted"
    assert not reopened.snapshot(scope)["artifacts"]
    reopened.db.engine.dispose()
