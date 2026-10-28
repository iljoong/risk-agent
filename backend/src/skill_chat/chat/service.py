import asyncio
import logging

from sqlalchemy import update

from skill_chat.chat.routing import Router
from skill_chat.contracts import AgentRequest, AppError, Gateway, InvalidInput, Scope, Unavailable
from skill_chat.documents.context import ContextBuilder
from skill_chat.extensions.registry import ExtensionRegistry
from skill_chat.storage.models import attachments, investigations, turns
from skill_chat.storage.repository import TERMINAL, Repository
from skill_chat.tasks.service import TaskService

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, repository: Repository, registry: ExtensionRegistry, gateway: Gateway):
        self.repo = repository
        self.registry = registry
        self.gateway = gateway
        self.tasks = TaskService(repository)
        self.router = Router(repository.settings, gateway)
        self.active: dict[str, asyncio.Task] = {}

    def receipt(self, scope: Scope, turn: dict) -> dict:
        task = next((t for t in self.repo.snapshot(scope)["tasks"] if t["turn_id"] == turn["id"]), None)
        return {
            "turn_id": turn["id"],
            "mode": turn["mode"],
            "task_id": task["id"] if task else None,
            "events_url": f"/api/chats/{scope.chat_id}/turns/{turn['id']}/events",
        }

    async def submit(self, scope: Scope, request: dict) -> dict:
        if not self.repo.settings.model(request["model_id"]):
            raise Unavailable("Selected model is no longer configured; choose an available model")
        if request.get("skill_id"):
            self.registry.get_skill(request["skill_id"])
        pending = False
        for attachment_id in request.get("attachment_ids", []):
            item = self.repo.get(attachments, scope, attachment_id)
            pending |= item["state"] != "ready"
        if request.get("artifact_version_id"):
            from skill_chat.artifacts.service import ArtifactService

            ArtifactService(self.repo).get(scope, request["artifact_version_id"])
        if self.repo.list_records(investigations, scope):
            from skill_chat.investigations.service import InvestigationService

            return InvestigationService(self.repo).submit_agent(scope, request, self.registry.fingerprint)
        turn, created = self.repo.create_turn(scope, request)
        if not created:
            for _ in range(60):
                turn = self.repo.get(turns, scope, turn["id"])
                if turn["state"] != "routing":
                    return self.receipt(scope, turn)
                await asyncio.sleep(0.1)
            raise Unavailable("The original request is still being routed; reload the chat")
        try:
            mode = await self.router.classify(
                scope,
                request["message"],
                pending,
                request.get("skill_id"),
                request["model_id"],
            )
        except TimeoutError:
            logger.warning("Intent classification timed out for turn %s; using background work", turn["id"])
            self.repo.add_event(
                scope,
                turn["id"],
                "stage",
                {"text": "Request classification timed out; switching to background processing."},
            )
            mode = "background"
        except (AppError, RuntimeError, ValueError, OSError) as error:
            message = (
                str(error)
                if isinstance(error, AppError)
                else f"Request routing failed ({type(error).__name__})"
            )
            with self.repo.db.transaction() as connection:
                connection.execute(
                    update(turns)
                    .where(
                        self.repo.owned(turns, scope),
                        turns.c.id == turn["id"],
                        turns.c.state == "routing",
                    )
                    .values(state="failed", error=message)
                )
            logger.error("Routing failed for turn %s: %s", turn["id"], type(error).__name__)
            raise Unavailable(message) from error
        if mode == "background":
            self.tasks.enqueue(
                scope, turn["id"], request["model_id"], request.get("skill_id"), self.registry.fingerprint
            )
        else:
            with self.repo.db.transaction() as connection:
                connection.execute(
                    update(turns)
                    .where(
                        self.repo.owned(turns, scope),
                        turns.c.id == turn["id"],
                        turns.c.state == "routing",
                    )
                    .values(state="pending", mode="foreground")
                )
        return self.receipt(scope, self.repo.get(turns, scope, turn["id"]))

    def claim_foreground(self, scope: Scope, turn_id: str) -> bool:
        with self.repo.db.transaction() as connection:
            result = connection.execute(
                update(turns)
                .where(
                    self.repo.owned(turns, scope),
                    turns.c.id == turn_id,
                    turns.c.mode == "foreground",
                    turns.c.state == "pending",
                )
                .values(state="running")
            )
            return result.rowcount == 1

    async def run_foreground(self, scope: Scope, turn_id: str):
        turn = self.repo.get(turns, scope, turn_id)
        request = turn["request"]
        answer = ""
        buffer = ""
        marker = "[BACKGROUND_REQUIRED]"
        try:
            messages = ContextBuilder(self.repo).build(
                scope,
                request["model_id"],
                request["message"],
                request.get("artifact_version_id"),
                turn_id,
            )
            async with asyncio.timeout(self.repo.settings.foreground_timeout_seconds):
                async for event in self.gateway.stream(
                    AgentRequest(
                        turn_id,
                        scope,
                        request["model_id"],
                        messages,
                        allow_tools=False,
                    )
                ):
                    if event.type == "error":
                        raise InvalidInput("Model response failed")
                    if event.type != "text_delta":
                        continue
                    buffer += event.text
                    if marker.startswith(buffer.strip()) and len(buffer.strip()) < len(marker):
                        continue
                    if buffer.strip().startswith(marker):
                        self.tasks.enqueue(
                            scope,
                            turn_id,
                            request["model_id"],
                            None,
                            self.registry.fingerprint,
                            expected_state="running",
                        )
                        self.repo.add_event(
                            scope, turn_id, "promoted", {"text": "Continuing as a background task"}
                        )
                        return
                    answer += buffer
                    self.repo.add_event(scope, turn_id, "text_delta", {"text": buffer})
                    self.repo.change(turns, scope, turn_id, answer=answer)
                    buffer = ""
            if not answer.strip():
                raise InvalidInput("Model returned no answer")
            self.repo.change(turns, scope, turn_id, state="succeeded", answer=answer)
            self.repo.add_event(scope, turn_id, "completed", {"state": "succeeded"})
        except asyncio.CancelledError:
            self.repo.change(
                turns,
                scope,
                turn_id,
                state="interrupted",
                answer=answer,
                error="Response stopped before completion",
            )
            self.repo.add_event(
                scope, turn_id, "error", {"state": "interrupted", "text": "Response interrupted"}
            )
        except (AppError, RuntimeError, ValueError, OSError, TimeoutError) as error:
            message = (
                str(error) if isinstance(error, AppError) else f"Response failed ({type(error).__name__})"
            )
            logger.error("Turn %s failed: %s", turn_id, type(error).__name__)
            self.repo.change(turns, scope, turn_id, state="failed", answer=answer, error=message)
            self.repo.add_event(scope, turn_id, "error", {"state": "failed", "text": message})
        finally:
            self.active.pop(turn_id, None)

    async def stream(self, scope: Scope, turn_id: str, after: int = 0):
        self.repo.get(turns, scope, turn_id)
        claimed = self.claim_foreground(scope, turn_id)
        if claimed:
            self.active[turn_id] = asyncio.create_task(self.run_foreground(scope, turn_id))
        try:
            while True:
                for event in self.repo.read_events(scope, turn_id, after):
                    after = event["id"]
                    yield event
                turn = self.repo.get(turns, scope, turn_id)
                if turn["state"] in TERMINAL:
                    # Flush events committed concurrently with the state change.
                    for event in self.repo.read_events(scope, turn_id, after):
                        after = event["id"]
                        yield event
                    return
                await asyncio.sleep(0.15)
        finally:
            turn = self.repo.get(turns, scope, turn_id)
            active = self.active.get(turn_id)
            if claimed and turn["mode"] == "foreground" and active:
                active.cancel()
                await asyncio.gather(active, return_exceptions=True)

    async def cancel_turn(self, scope: Scope, turn_id: str):
        self.repo.get(turns, scope, turn_id)
        with self.repo.db.transaction() as connection:
            cancelled = (
                connection.execute(
                    update(turns)
                    .where(
                        self.repo.owned(turns, scope),
                        turns.c.id == turn_id,
                        turns.c.state.in_(["pending", "routing"]),
                    )
                    .values(state="cancelled")
                ).rowcount
                == 1
            )
        if cancelled:
            self.repo.add_event(scope, turn_id, "error", {"state": "cancelled", "text": "Request cancelled"})
            return self.repo.get(turns, scope, turn_id)
        turn = self.repo.get(turns, scope, turn_id)
        if turn["mode"] == "background":
            for task in self.repo.snapshot(scope)["tasks"]:
                if task["turn_id"] == turn_id:
                    return self.tasks.request_cancel(scope, task["id"])
        active = self.active.get(turn_id)
        if active:
            active.cancel()
            await asyncio.gather(active, return_exceptions=True)
        return self.repo.get(turns, scope, turn_id)

    def recover_foreground(self):
        with self.repo.db.transaction() as connection:
            connection.execute(
                update(turns)
                .where(
                    turns.c.mode == "foreground",
                    turns.c.state.in_(["running", "pending", "routing"]),
                )
                .values(state="interrupted", error="API restarted before the response completed")
            )

    async def close(self):
        jobs = list(self.active.values())
        for job in jobs:
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
