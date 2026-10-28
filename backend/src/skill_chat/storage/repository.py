from __future__ import annotations

import re
import time
from contextlib import nullcontext
from uuid import uuid4

from sqlalchemy import delete, insert, select, update

from skill_chat.config import Settings
from skill_chat.contracts import Conflict, NotFound, Scope
from skill_chat.storage.database import Database
from skill_chat.storage.files import FileStore
from skill_chat.storage.models import artifacts, attachments, chats, events, investigations, tasks, turns

ACTIVE = ("pending", "routing", "queued", "running", "cancel_requested")
TERMINAL = ("succeeded", "failed", "cancelled", "interrupted")


class Repository:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings)
        self.files = FileStore(settings.data_dir)
        self.cleanup_deleted_chats()
        with self.db.engine.connect() as connection:
            scopes = list(connection.execute(select(chats.c.owner_id, chats.c.id)))
        for owner_id, chat_id in scopes:
            self.cleanup_orphan_files(Scope(owner_id, chat_id))

    def cleanup_orphan_files(self, scope: Scope):
        referenced = {
            item["id"] for table in (attachments, artifacts) for item in self.list_records(table, scope)
        }
        cutoff = time.time() - 60
        for file in self.files.root_for(scope).iterdir():
            if not re.fullmatch(r"(?:staged-)?[a-f0-9]{32}", file.name) or file.name in referenced:
                continue
            checked = self.files.resolve(scope, file.name)
            # Writes precede their records; leave a grace period for in-flight publication.
            if checked.is_file() and checked.stat().st_mtime < cutoff:
                checked.unlink()

    def create_chat(self, owner_id: str, model_id: str, title: str = "New chat") -> dict:
        data = {
            "id": uuid4().hex,
            "owner_id": owner_id,
            "model_id": model_id,
            "title": title,
            "created": time.time(),
            "deleting": 0,
        }
        with self.db.transaction() as connection:
            connection.execute(insert(chats).values(**data))
        return data

    def list_chats(self, owner_id: str) -> list[dict]:
        with self.db.engine.connect() as connection:
            result = [
                dict(row)
                for row in connection.execute(
                    select(chats)
                    .where(chats.c.owner_id == owner_id, chats.c.deleting == 0)
                    .order_by(chats.c.created.desc())
                ).mappings()
            ]
            cases = {
                row["chat_id"]: row["state"]
                for row in connection.execute(select(investigations).where(
                    investigations.c.owner_id == owner_id,
                )).mappings()
            }
            return [{**item, "investigation": (
                {"case_id": cases[item["id"]]["case_id"],
                 "current_stage": cases[item["id"]]["current_stage"], "connector": "demo"}
                if item["id"] in cases else None
            )} for item in result]

    def get_chat(self, scope: Scope) -> dict:
        with self.db.engine.connect() as connection:
            row = (
                connection.execute(
                    select(chats).where(
                        chats.c.id == scope.chat_id, chats.c.owner_id == scope.owner_id, chats.c.deleting == 0
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise NotFound("Chat not found")
        return dict(row)

    @staticmethod
    def owned(table, scope: Scope):
        return (table.c.owner_id == scope.owner_id) & (table.c.chat_id == scope.chat_id)

    def get(self, table, scope: Scope, object_id: str) -> dict:
        self.get_chat(scope)
        with self.db.engine.connect() as connection:
            row = (
                connection.execute(select(table).where(self.owned(table, scope), table.c.id == object_id))
                .mappings()
                .first()
            )
        if row is None:
            raise NotFound("Object not found in this chat")
        return dict(row)

    def list_records(self, table, scope: Scope) -> list[dict]:
        self.get_chat(scope)
        with self.db.engine.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(table).where(self.owned(table, scope)).order_by(table.c.created)
                ).mappings()
            ]

    def busy(self, connection, scope: Scope) -> bool:
        return (
            connection.execute(
                select(turns.c.id).where(self.owned(turns, scope), turns.c.state.in_(ACTIVE))
            ).first()
            is not None
        )

    def rename_chat(self, scope: Scope, title: str, model_id: str | None = None) -> dict:
        self.get_chat(scope)
        with self.db.transaction() as connection:
            if model_id and self.busy(connection, scope):
                raise Conflict("Stop active work before changing the model")
            values = {"title": title}
            if model_id:
                values["model_id"] = model_id
            connection.execute(
                update(chats)
                .where(chats.c.id == scope.chat_id, chats.c.owner_id == scope.owner_id)
                .values(**values)
            )
        return self.get_chat(scope)

    def delete_chat(self, scope: Scope):
        self.get_chat(scope)
        with self.db.transaction() as connection:
            if self.busy(connection, scope):
                raise Conflict("Stop active work before deleting this chat")
            connection.execute(
                update(chats)
                .where(chats.c.id == scope.chat_id, chats.c.owner_id == scope.owner_id)
                .values(deleting=1)
            )
        self.cleanup_deleted_chats()

    def cleanup_deleted_chats(self):
        with self.db.engine.connect() as connection:
            pending = list(connection.execute(select(chats).where(chats.c.deleting == 1)).mappings())
        for chat in pending:
            self.files.delete_chat(Scope(chat["owner_id"], chat["id"]))
            with self.db.transaction() as connection:
                connection.execute(delete(chats).where(chats.c.id == chat["id"], chats.c.deleting == 1))

    def create_turn(self, scope: Scope, request: dict, *, connection=None) -> tuple[dict, bool]:
        self.get_chat(scope)
        with self.db.transaction() if connection is None else nullcontext(connection) as conn:
            existing = (
                conn.execute(
                    select(turns).where(
                        self.owned(turns, scope), turns.c.client_request_id == request["client_request_id"]
                    )
                )
                .mappings()
                .first()
            )
            if existing:
                if existing["request"] != request:
                    raise Conflict("Request ID was reused with different content")
                return dict(existing), False
            if self.busy(conn, scope):
                raise Conflict("This chat already has active work")
            data = {
                "id": uuid4().hex,
                "owner_id": scope.owner_id,
                "chat_id": scope.chat_id,
                "created": time.time(),
                "client_request_id": request["client_request_id"],
                "request": request,
                "state": "routing",
                "mode": "foreground",
                "answer": "",
                "error": None,
            }
            conn.execute(insert(turns).values(**data))
        return data, True

    def change(self, table, scope: Scope, object_id: str, **values):
        self.get(table, scope, object_id)
        with self.db.transaction() as connection:
            connection.execute(
                update(table).where(self.owned(table, scope), table.c.id == object_id).values(**values)
            )

    def add_event(self, scope: Scope, turn_id: str, event_type: str, data: dict):
        self.get(turns, scope, turn_id)
        with self.db.transaction() as connection:
            connection.execute(
                insert(events).values(
                    owner_id=scope.owner_id,
                    chat_id=scope.chat_id,
                    turn_id=turn_id,
                    type=event_type,
                    data=data,
                )
            )

    def read_events(self, scope: Scope, turn_id: str, after: int = 0) -> list[dict]:
        self.get(turns, scope, turn_id)
        with self.db.engine.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    select(events)
                    .where(
                        self.owned(events, scope),
                        events.c.turn_id == turn_id,
                        events.c.id > after,
                    )
                    .order_by(events.c.id)
                ).mappings()
            ]

    def snapshot(self, scope: Scope) -> dict:
        return {
            **self.get_chat(scope),
            "turns": self.list_records(turns, scope),
            "attachments": [
                {key: value for key, value in item.items() if key != "pages"}
                for item in self.list_records(attachments, scope)
            ],
            "tasks": self.list_records(tasks, scope),
            "artifacts": [
                item for item in self.list_records(artifacts, scope) if item["state"] == "published"
            ],
        }
