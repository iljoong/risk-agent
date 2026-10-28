import asyncio
import logging
import time
from uuid import uuid4

from sqlalchemy import select

from skill_chat.agents.gateway import AgentGateway
from skill_chat.config import load_settings
from skill_chat.contracts import AgentRequest, AppError, Gateway, InvalidInput, Scope
from skill_chat.documents.context import ContextBuilder
from skill_chat.documents.ingestion import AttachmentService
from skill_chat.extensions.registry import ExtensionRegistry, build_registry
from skill_chat.investigations.connector import (
    DemoInvestigationConnector,
    InvestigationConnector,
    collect_sources,
)
from skill_chat.investigations.service import InvestigationService
from skill_chat.storage.models import artifacts, turns
from skill_chat.storage.models import attachments as attachment_rows
from skill_chat.storage.repository import Repository
from skill_chat.tasks.service import TaskService

logger = logging.getLogger(__name__)


class Worker:
    def __init__(
        self, repository: Repository, registry: ExtensionRegistry, gateway: Gateway,
        connector: InvestigationConnector | None = None,
    ):
        self.repo = repository
        self.registry = registry
        self.gateway = gateway
        self.tasks = TaskService(repository)
        self.id = uuid4().hex
        self.connector = connector or DemoInvestigationConnector()

    async def execute(self, scope: Scope, task: dict):
        if task["fingerprint"] != self.registry.fingerprint:
            raise InvalidInput("Extensions changed; send a new request after restarting API and worker")
        if task["skill_id"]:
            self.registry.get_skill(task["skill_id"])
        turn = self.repo.get(turns, scope, task["turn_id"])
        request = turn["request"]
        if request.get("investigation", {}).get("operation") == "prepare":
            await collect_sources(InvestigationService(self.repo), scope, task, self.connector, self.tasks)
            return
        attachments = AttachmentService(self.repo)
        for attachment_id in request.get("attachment_ids", []):
            self.tasks.stage(scope, task["id"], "Reading attached PDF")
            await asyncio.to_thread(attachments.ingest, scope, attachment_id)
        if task["skill_id"] == "rfp-response" and not any(
            attachment["state"] == "ready" for attachment in self.repo.list_records(attachment_rows, scope)
        ):
            raise InvalidInput("Attach at least one text-based RFP PDF before running this skill.")
        self.tasks.stage(scope, task["id"], "Preparing source context")
        messages = ContextBuilder(self.repo).build(
            scope,
            task["model_id"],
            request["message"],
            request.get("artifact_version_id"),
            turn["id"],
            allow_tools=True,
        )
        self.tasks.stage(scope, task["id"], "Running skill" if task["skill_id"] else "Working on your task")
        answer = ""
        async for event in self.gateway.stream(
            AgentRequest(
                run_id=turn["id"],
                scope=scope,
                model_id=task["model_id"],
                messages=messages,
                skill_id=task["skill_id"],
                task_id=task["id"],
            )
        ):
            if event.type == "error":
                raise InvalidInput("Agent reported an execution error")
            if event.type == "text_delta":
                answer += event.text
                self.repo.change(turns, scope, turn["id"], answer=answer)
            if event.type != "completed":
                self.repo.add_event(scope, turn["id"], event.type, event.model_dump(exclude={"type"}))
        if answer.strip() == "[BACKGROUND_REQUIRED]":
            raise InvalidInput("Background task returned a routing marker instead of an answer; retry.")
        if task["skill_id"] == "rfp-response":
            with self.repo.db.engine.connect() as connection:
                saved = connection.execute(
                    select(artifacts.c.id).where(
                        self.repo.owned(artifacts, scope),
                        artifacts.c.task_id == task["id"],
                    )
                ).first()
            if saved is None:
                raise InvalidInput("The RFP skill did not publish HTML slides. Retry or refine the request.")
        self.tasks.finish(scope, task["id"], "succeeded", answer)

    async def run_once(self) -> bool:
        self.tasks.recover_expired()
        self.tasks.heartbeat(None, self.id)
        task = self.tasks.claim_next(self.id)
        if not task:
            return False
        scope = Scope(task["owner_id"], task["chat_id"])
        job = asyncio.create_task(self.execute(scope, task))
        start = time.monotonic()
        try:
            while not job.done():
                self.tasks.heartbeat(task["id"], self.id)
                if self.tasks.get(scope, task["id"])["state"] == "cancel_requested":
                    await self.gateway.cancel(task["turn_id"])
                    job.cancel()
                if time.monotonic() - start > self.repo.settings.background_timeout_seconds:
                    job.cancel()
                    raise TimeoutError("Background task exceeded its configured deadline")
                await asyncio.wait({job}, timeout=0.5)
            await job
        except asyncio.CancelledError:
            job.cancel()
            await asyncio.gather(job, return_exceptions=True)
            self.tasks.finish(
                scope, task["id"], "cancelled", self.repo.get(turns, scope, task["turn_id"])["answer"]
            )
        except (AppError, RuntimeError, ValueError, OSError, TimeoutError) as error:
            job.cancel()
            await asyncio.gather(job, return_exceptions=True)
            message = (
                str(error)
                if isinstance(error, AppError)
                else f"Execution failed ({type(error).__name__}). Check provider access and server logs."
            )
            logger.error("Task %s failed: %s", task["id"], type(error).__name__)
            self.tasks.finish(scope, task["id"], "failed", error=message)
        return True


async def main():
    settings = load_settings()
    repo = Repository(settings)
    registry = build_registry(repo)
    gateway = AgentGateway(settings, registry)
    worker = Worker(repo, registry, gateway)
    try:
        while True:
            if not await worker.run_once():
                await asyncio.sleep(1)
    finally:
        await gateway.close()
        repo.db.engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
