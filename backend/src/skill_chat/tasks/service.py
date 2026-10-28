import time
from contextlib import nullcontext
from uuid import uuid4

from sqlalchemy import insert, select, update

from skill_chat.contracts import Conflict, NotFound, Scope, Unavailable
from skill_chat.storage.models import artifacts, events, tasks, turns, worker_status
from skill_chat.storage.repository import Repository


class TaskService:
    def __init__(self, repository: Repository):
        self.repo = repository

    def enqueue(
        self,
        scope: Scope,
        turn_id: str,
        model_id: str,
        skill_id: str | None,
        registry_fingerprint: str,
        retry_of: str | None = None,
        *,
        expected_state: str = "routing",
        connection=None,
    ) -> dict:
        data = {
            "id": uuid4().hex,
            "owner_id": scope.owner_id,
            "chat_id": scope.chat_id,
            "turn_id": turn_id,
            "model_id": model_id,
            "skill_id": skill_id,
            "fingerprint": registry_fingerprint,
            "state": "queued",
            "stage": "Queued",
            "created": time.time(),
            "retry_of": retry_of,
            "worker_id": None,
            "heartbeat": None,
            "error": None,
            "finished": None,
        }
        with self.repo.db.transaction() if connection is None else nullcontext(connection) as conn:
            if not conn.execute(select(turns.c.id).where(
                self.repo.owned(turns, scope), turns.c.id == turn_id,
            )).first():
                raise NotFound("Turn not found in this session")
            changed = conn.execute(
                update(turns)
                .where(self.repo.owned(turns, scope), turns.c.id == turn_id, turns.c.state == expected_state)
                .values(state="queued", mode="background")
            )
            if changed.rowcount != 1:
                raise Conflict("This turn no longer accepts work; it may have been stopped.")
            conn.execute(insert(tasks).values(**data))
        return data

    def get(self, scope: Scope, task_id: str) -> dict:
        return self.repo.get(tasks, scope, task_id)

    def claim_next(self, worker_id: str) -> dict | None:
        with self.repo.db.transaction() as connection:
            # The local deployment intentionally allows only one global background execution.
            if connection.execute(
                select(tasks.c.id).where(tasks.c.state.in_(["running", "cancel_requested"]))
            ).first():
                return None
            row = (
                connection.execute(select(tasks).where(tasks.c.state == "queued").order_by(tasks.c.created))
                .mappings()
                .first()
            )
            if row is None:
                return None
            data = dict(row)
            connection.execute(
                update(tasks)
                .where(tasks.c.id == data["id"])
                .values(
                    state="running",
                    worker_id=worker_id,
                    heartbeat=time.time(),
                    stage="Starting",
                )
            )
            connection.execute(update(turns).where(turns.c.id == data["turn_id"]).values(state="running"))
        return {**data, "state": "running", "worker_id": worker_id}

    def heartbeat(self, task_id: str | None, worker_id: str):
        with self.repo.db.transaction() as connection:
            existing = connection.execute(
                select(worker_status).where(worker_status.c.id == worker_id)
            ).first()
            if existing:
                connection.execute(
                    update(worker_status).where(worker_status.c.id == worker_id).values(heartbeat=time.time())
                )
            else:
                connection.execute(insert(worker_status).values(id=worker_id, heartbeat=time.time()))
            if task_id:
                connection.execute(
                    update(tasks)
                    .where(
                        tasks.c.id == task_id,
                        tasks.c.worker_id == worker_id,
                        tasks.c.state.in_(["running", "cancel_requested"]),
                    )
                    .values(heartbeat=time.time())
                )

    def request_cancel(self, scope: Scope, task_id: str) -> dict:
        self.get(scope, task_id)
        with self.repo.db.transaction() as connection:
            row = (
                connection.execute(select(tasks).where(self.repo.owned(tasks, scope), tasks.c.id == task_id))
                .mappings()
                .one()
            )
            if row["state"] == "queued":
                self._finish(connection, scope, dict(row), "cancelled", "", None)
            elif row["state"] == "running":
                connection.execute(
                    update(tasks).where(tasks.c.id == task_id).values(state="cancel_requested")
                )
        return self.get(scope, task_id)

    def stage(self, scope: Scope, task_id: str, text: str):
        task = self.get(scope, task_id)
        self.repo.change(tasks, scope, task_id, stage=text)
        self.repo.add_event(scope, task["turn_id"], "stage", {"text": text})

    def _finish(
        self, connection, scope: Scope, task: dict, state: str, answer: str | None, error: str | None
    ):
        if task["state"] not in {"queued", "running", "cancel_requested"}:
            return
        if task["state"] == "cancel_requested":
            state = "cancelled"
        from skill_chat.investigations.service import InvestigationService

        InvestigationService(self.repo).publish_candidates(connection, scope, task, state)
        turn_values = {"state": state, "error": error}
        if answer is not None:
            turn_values["answer"] = answer
        connection.execute(
            update(tasks)
            .where(tasks.c.id == task["id"])
            .values(
                state=state,
                error=error,
                finished=time.time(),
                stage=state.capitalize(),
            )
        )
        connection.execute(
            update(turns)
            .where(self.repo.owned(turns, scope), turns.c.id == task["turn_id"])
            .values(**turn_values)
        )
        if state == "succeeded":
            staged = list(
                connection.execute(
                    select(artifacts).where(
                        self.repo.owned(artifacts, scope),
                        artifacts.c.task_id == task["id"],
                        artifacts.c.state == "staged",
                    )
                ).mappings()
            )
            connection.execute(
                update(artifacts)
                .where(
                    self.repo.owned(artifacts, scope),
                    artifacts.c.task_id == task["id"],
                )
                .values(state="published")
            )
            for item in staged:
                connection.execute(
                    insert(events).values(
                        owner_id=scope.owner_id,
                        chat_id=scope.chat_id,
                        turn_id=task["turn_id"],
                        type="artifact",
                        data={"artifact_id": item["id"], "title": item["title"], "version": item["version"]},
                    )
                )
        connection.execute(
            insert(events).values(
                owner_id=scope.owner_id,
                chat_id=scope.chat_id,
                turn_id=task["turn_id"],
                type="completed" if state == "succeeded" else "error",
                data={"state": state, "text": error or state.capitalize()},
            )
        )

    def finish(
        self, scope: Scope, task_id: str, state: str, answer: str | None = None, error: str | None = None
    ):
        self.get(scope, task_id)
        with self.repo.db.transaction() as connection:
            task = (
                connection.execute(select(tasks).where(self.repo.owned(tasks, scope), tasks.c.id == task_id))
                .mappings()
                .one()
            )
            self._finish(connection, scope, dict(task), state, answer, error)

    def recover_expired(self) -> int:
        with self.repo.db.transaction() as connection:
            expired = list(
                connection.execute(
                    select(tasks).where(
                        tasks.c.state.in_(["running", "cancel_requested"]),
                        tasks.c.heartbeat < time.time() - 60,
                    )
                ).mappings()
            )
            for task in expired:
                scope = Scope(task["owner_id"], task["chat_id"])
                self._finish(
                    connection,
                    scope,
                    dict(task),
                    "interrupted",
                    None,
                    "Worker stopped during execution. Retry explicitly to run again.",
                )
        return len(expired)

    def retry(self, scope: Scope, task_id: str, registry_fingerprint: str) -> dict:
        task = self.get(scope, task_id)
        if task["state"] not in {"failed", "cancelled", "interrupted"}:
            raise Conflict("Only failed, cancelled or interrupted tasks can be retried")
        if not self.repo.settings.model(task["model_id"]):
            raise Unavailable("Original model is no longer configured")
        if task["fingerprint"] != registry_fingerprint:
            raise Conflict("Extensions changed; send a new request with the current skill")
        original = self.repo.get(turns, scope, task["turn_id"])
        request = {**original["request"], "client_request_id": uuid4().hex}
        turn, _ = self.repo.create_turn(scope, request)
        return self.enqueue(
            scope, turn["id"], task["model_id"], task["skill_id"], registry_fingerprint, task_id
        )
