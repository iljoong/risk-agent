import copy
import json
import time
from uuid import uuid4

from ag_ui.core import ActivitySnapshotEvent, EventType, StateSnapshotEvent
from pydantic import BaseModel, ValidationError
from sqlalchemy import insert, select, update

from skill_chat.contracts import Conflict, InvalidInput, NotFound, Scope, Unavailable
from skill_chat.investigations.schemas import (
    MAX_UI_EVENT_BYTES,
    STAGES,
    AmendFact,
    AmendOutput,
    ClarificationIdentity,
    Empty,
    InvestigationCommand,
    InvestigationSnapshot,
    ResolveClarification,
    ReviewNote,
    SelectStage,
    StageOutput,
)
from skill_chat.investigations.surfaces import SCOPE_QUESTION, build_scope_surface, validate_scope_surface
from skill_chat.storage.models import (
    chats,
    investigation_candidates,
    investigation_commands,
    investigation_revisions,
    investigation_ui_events,
    investigations,
    tasks,
    turns,
)
from skill_chat.storage.repository import Repository


class InvestigationService:
    def __init__(self, repository: Repository):
        self.repo = repository

    def row(self, connection, scope: Scope) -> dict:
        row = connection.execute(
            select(investigations).where(self.repo.owned(investigations, scope))
        ).mappings().first()
        if row is None:
            raise NotFound("Investigation not found in this session")
        return dict(row)

    def get(self, scope: Scope) -> dict:
        self.repo.get_chat(scope)
        with self.repo.db.engine.connect() as connection:
            return copy.deepcopy(self.project(self.row(connection, scope)["state"]))

    @staticmethod
    def project(state: dict) -> dict:
        fields = ("actor", "action", "revision", "timestamp", "stage_id", "reason")
        return {**state, "history": [
            {key: record[key] for key in fields if key in record}
            for record in state["history"][-20:]
        ]}

    def history(self, scope: Scope, before: int | None = None, limit: int = 10) -> dict:
        if not 1 <= limit <= 10:
            raise InvalidInput("Revision history page size must be between 1 and 10")
        self.repo.get_chat(scope)
        with self.repo.db.engine.connect() as connection:
            self.row(connection, scope)
            query = select(investigation_revisions).where(self.repo.owned(investigation_revisions, scope))
            if before is not None:
                query = query.where(investigation_revisions.c.revision < before)
            rows = list(connection.execute(
                query.order_by(investigation_revisions.c.revision.desc()).limit(limit + 1),
            ).mappings())
            return {"records": [row["record"] for row in rows[:limit]],
                    "next_before": rows[limit - 1]["revision"] if len(rows) > limit else None}

    def create(self, owner_id: str, model_id: str, client_request_id: str) -> dict:
        if not self.repo.settings.model(model_id):
            raise Unavailable("Selected model is not configured")
        with self.repo.db.transaction() as connection:
            existing = connection.execute(select(investigations).where(
                investigations.c.owner_id == owner_id,
                investigations.c.creation_request_id == client_request_id,
            )).mappings().first()
            if existing:
                if existing["model_id"] != model_id:
                    raise Conflict("Creation request ID was reused with a different model")
                return {"chat_id": existing["chat_id"], "revision": existing["revision"]}
            chat_id = uuid4().hex
            now = time.time()
            connection.execute(insert(chats).values(
                id=chat_id, owner_id=owner_id, title="Harbour Components Ltd / CASE-1041",
                model_id=model_id, created=now, deleting=0,
            ))
            state = InvestigationSnapshot(
                chat_id=chat_id, case_id="CASE-1041", connector="demo", revision=1,
                current_stage="investigate",
                original_alert={"id": "ALT-2041", "priority": "High",
                                "trigger": "Rapid movement of funds to a newly observed beneficiary"},
                shared_facts={"beneficiary_description": "Beneficiary not observed in the available 90-day history"},
                sources=[], history=[],
                outputs={stage: StageOutput(text=(
                    "Original alert ALT-2041: High priority from the existing fictional AML system."
                    if stage == "detect" else
                    "Assess the payment pattern and plausible supplier explanation using permitted demo sources."
                    if stage == "investigate" else "Awaiting investigation preparation and human assessment."
                ), version=1, needs_review=True) for stage in STAGES},
                review={"reviewed": False, "rationale": "", "prepared_note": None},
            ).model_dump()
            connection.execute(insert(investigations).values(
                id=uuid4().hex, owner_id=owner_id, chat_id=chat_id, created=now,
                creation_request_id=client_request_id, model_id=model_id, revision=1, state=state,
            ))
            self.emit(connection, Scope(owner_id, chat_id), state)
            return {"chat_id": chat_id, "revision": 1}

    def emit(self, connection, scope: Scope, state: dict) -> int:
        payload = StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=self.project(state)).model_dump(
            mode="json", by_alias=True, exclude_none=True,
        )
        if len(json.dumps(payload, ensure_ascii=False).encode()) + 128 > MAX_UI_EVENT_BYTES:
            raise InvalidInput("Investigation projection exceeds the UI event size limit")
        result = connection.execute(insert(investigation_ui_events).values(
            owner_id=scope.owner_id, chat_id=scope.chat_id, created=time.time(),
            payload=payload,
        ))
        sequence = int(result.inserted_primary_key[0])
        clarification = state.get("clarification")
        if clarification:
            activity = ActivitySnapshotEvent(
                type=EventType.ACTIVITY_SNAPSHOT, message_id=clarification["id"], activity_type="a2ui-surface",
                content={"revision": clarification["surface_revision"], "status": clarification["status"],
                         "a2ui_operations": clarification["operations"] if clarification["status"] == "pending" else []},
            )
            result = connection.execute(insert(investigation_ui_events).values(
                owner_id=scope.owner_id, chat_id=scope.chat_id, created=time.time(),
                payload=activity.model_dump(mode="json", by_alias=True, exclude_none=True),
            ))
            sequence = int(result.inserted_primary_key[0])
        return sequence

    def save(self, connection, scope: Scope, state: dict, record: dict) -> int:
        state["revision"] += 1
        record = {**record, "revision": state["revision"], "timestamp": time.time()}
        state["history"].append(record)
        state["history"] = self.project(state)["history"]
        state = InvestigationSnapshot.model_validate(state).model_dump()
        connection.execute(update(investigations).where(self.repo.owned(investigations, scope)).values(
            revision=state["revision"], state=state,
        ))
        connection.execute(insert(investigation_revisions).values(
            id=uuid4().hex, owner_id=scope.owner_id, chat_id=scope.chat_id,
            created=record["timestamp"], revision=state["revision"], record=record,
        ))
        return self.emit(connection, scope, state)

    @staticmethod
    def invalidate(state: dict, stages: list[str]):
        for stage in stages:
            state["outputs"][stage]["needs_review"] = True
        state["review"]["reviewed"] = False
        state["review"]["prepared_note"] = None

    @staticmethod
    def note(state: dict) -> str:
        gaps = [f"{item['id']}: {item['title']}" for item in state["evidence"]
                if item["kind"] in ("Missing information", "Access limitation")]
        references = [item["id"] for item in state["evidence"]]
        references.extend(
            f"{source['source_id']} / {source['version']}" for source in state["sources"]
            if source["status"] == "available" and source.get("version")
        )
        parts = [
            f"CASE-1041 / Harbour Components Ltd / revision {state['revision']}",
            "FICTIONAL DEMO RECORDS. Draft for human review, not a financial or compliance determination.",
            state["shared_facts"]["beneficiary_description"],
        ]
        parts.extend(
            f"{stage} / output v{item['version']}\n{item['text']}"
            for stage, item in state["outputs"].items()
        )
        parts.extend([
            f"Analyst rationale: {state['review']['rationale']}",
            f"Remaining recorded gaps: {'; '.join(gaps) or 'No evidence collected.'}",
            f"References: {'; '.join(references) or 'No references collected.'}",
            "External saving / approval: unconfirmed. Copying is not saving, closing or approving.",
        ])
        return "\n\n".join(parts)

    def prepare(self, scope: Scope, command: InvestigationCommand, registry_fingerprint: str) -> dict:
        if command.action != "prepare":
            raise InvalidInput("Expected a preparation action")
        return self.apply(scope, command, registry_fingerprint=registry_fingerprint)

    def queue(self, connection, scope: Scope, state: dict, request_id: str, message: str,
              fingerprint: str, operation: str = "agent") -> dict:
        from skill_chat.tasks.service import TaskService

        chat = self.repo.get_chat(scope)
        request = {
            "client_request_id": request_id, "message": message, "model_id": chat["model_id"],
            "skill_id": None, "attachment_ids": [], "artifact_version_id": None,
            "investigation": {"operation": operation, "base_revision": state["revision"], "snapshot": state},
        }
        turn, _ = self.repo.create_turn(scope, request, connection=connection)
        task = TaskService(self.repo).enqueue(
            scope, turn["id"], chat["model_id"], None, fingerprint, connection=connection,
        )
        return {"turn_id": turn["id"], "task_id": task["id"]}

    def submit_agent(self, scope: Scope, request: dict, fingerprint: str) -> dict:
        from skill_chat.tasks.service import TaskService

        with self.repo.db.transaction() as connection:
            existing = connection.execute(select(turns).where(
                self.repo.owned(turns, scope), turns.c.client_request_id == request["client_request_id"],
            )).mappings().first()
            if existing:
                public = {key: value for key, value in existing["request"].items() if key != "investigation"}
                if public != request:
                    raise Conflict("Request ID was reused with different content")
                task = connection.execute(select(tasks).where(
                    self.repo.owned(tasks, scope), tasks.c.turn_id == existing["id"],
                )).mappings().one()
                return {"turn_id": existing["id"], "task_id": task["id"], "mode": "background",
                        "events_url": f"/api/chats/{scope.chat_id}/turns/{existing['id']}/events"}
            state = copy.deepcopy(self.row(connection, scope)["state"])
            internal = {**request, "investigation": {
                "operation": "agent", "base_revision": state["revision"], "snapshot": state,
            }}
            turn, _ = self.repo.create_turn(scope, internal, connection=connection)
            task = TaskService(self.repo).enqueue(
                scope, turn["id"], request["model_id"], request.get("skill_id"), fingerprint,
                connection=connection,
            )
            return {"turn_id": turn["id"], "task_id": task["id"], "mode": "background",
                    "events_url": f"/api/chats/{scope.chat_id}/turns/{turn['id']}/events"}

    def stage_candidate(self, scope: Scope, task_id: str, base_revision: int, payload: dict):
        from skill_chat.storage.models import tasks

        with self.repo.db.transaction() as connection:
            task = connection.execute(select(tasks).where(
                self.repo.owned(tasks, scope), tasks.c.id == task_id,
            )).mappings().first()
            if not task or task["state"] != "running":
                raise Conflict("Task is no longer accepting investigation output")
            state = self.row(connection, scope)["state"]
            if state["revision"] != base_revision:
                raise Conflict("Investigation changed since the task started; submit a new request")
            candidate = connection.execute(select(investigation_candidates).where(
                self.repo.owned(investigation_candidates, scope),
                investigation_candidates.c.task_id == task_id,
            )).mappings().first()
            if candidate:
                merged = {**candidate["payload"], **payload}
                if "output_updates" in payload:
                    merged["output_updates"] = {
                        **candidate["payload"].get("output_updates", {}), **payload["output_updates"],
                    }
                connection.execute(update(investigation_candidates).where(
                    investigation_candidates.c.id == candidate["id"],
                ).values(payload=merged))
            else:
                connection.execute(insert(investigation_candidates).values(
                    id=uuid4().hex, owner_id=scope.owner_id, chat_id=scope.chat_id, created=time.time(),
                    task_id=task_id, base_revision=base_revision, payload=payload,
                ))

    def publish_candidates(self, connection, scope: Scope, task: dict, terminal_state: str):
        candidate = connection.execute(select(investigation_candidates).where(
            self.repo.owned(investigation_candidates, scope),
            investigation_candidates.c.task_id == task["id"],
        )).mappings().first()
        if not candidate or terminal_state != "succeeded":
            return
        state = copy.deepcopy(self.row(connection, scope)["state"])
        if state["revision"] != candidate["base_revision"]:
            raise Conflict("Investigation changed; outdated task output cannot be published")
        payload = candidate["payload"]
        for field in ("sources", "transactions", "evidence", "calculations", "prepared"):
            if field in payload:
                state[field] = payload[field]
        for stage, output in payload.get("output_updates", {}).items():
            state["outputs"][stage].update(output)
            state["outputs"][stage]["version"] += 1
            self.invalidate(state, list(STAGES[STAGES.index(stage):]))
        state["current_stage"] = "analyze" if payload.get("prepared") else state["current_stage"]
        self.save(connection, scope, state, {
            "actor": "demo_connector" if payload.get("prepared") else "agent",
            "action": "publish_task_output", "task_id": task["id"],
            "output_updates": payload.get("output_updates", {}),
        })

    def apply(
        self, scope: Scope, command: InvestigationCommand, *, registry_fingerprint: str | None = None,
    ) -> dict:
        self.repo.get_chat(scope)
        with self.repo.db.transaction() as connection:
            existing = connection.execute(select(investigation_commands).where(
                self.repo.owned(investigation_commands, scope),
                investigation_commands.c.client_request_id == command.client_request_id,
            )).mappings().first()
            body = command.model_dump()
            if existing:
                if existing["request"] != body:
                    raise Conflict("Request ID was reused with different content")
                return existing["receipt"]
            state = copy.deepcopy(self.row(connection, scope)["state"])
            if state["revision"] != command.expected_revision:
                raise Conflict("Investigation changed. Refresh and reapply your saved draft.")
            if self.repo.busy(connection, scope):
                raise Conflict("Wait for active work before changing the investigation")
            models: dict[str, type[BaseModel]] = {
                "amend_output": AmendOutput, "amend_fact": AmendFact,
                "acknowledge_stage": SelectStage, "select_stage": SelectStage,
                "review_note": ReviewNote, "prepare_note": Empty,
                "prepare": Empty, "request_clarification": Empty,
                "resolve_clarification": ResolveClarification, "cancel_clarification": ClarificationIdentity,
            }
            if command.action not in models:
                raise InvalidInput("Unsupported investigation action")
            try:
                payload = models[command.action].model_validate(command.payload).model_dump()
            except ValidationError as error:
                raise InvalidInput("Invalid investigation amendment or action fields") from error
            record = {"actor": "analyst", "action": command.action,
                      "request_id": command.client_request_id, "reason": payload.get("reason", "")}
            if command.action == "prepare":
                if not registry_fingerprint:
                    raise InvalidInput("Preparation requires the server's extension registry")
                state["current_stage"] = "gather_evidence"
                self.invalidate(state, list(STAGES[2:]))
            elif command.action == "amend_output":
                stage = payload["stage_id"]
                output = state["outputs"][stage]
                record.update(stage_id=stage, before=output["text"], after=payload["text"])
                output["text"] = payload["text"]
                output["version"] += 1
                self.invalidate(state, list(STAGES[STAGES.index(stage):]))
            elif command.action == "amend_fact":
                record.update(before=state["shared_facts"]["beneficiary_description"],
                              after=payload["beneficiary_description"])
                state["shared_facts"]["beneficiary_description"] = payload["beneficiary_description"]
                self.invalidate(state, list(STAGES))
            elif command.action == "acknowledge_stage":
                state["outputs"][payload["stage_id"]]["needs_review"] = False
                record["stage_id"] = payload["stage_id"]
            elif command.action == "select_stage":
                state["current_stage"] = payload["stage_id"]
            elif command.action == "review_note":
                if not state["prepared"]:
                    raise Conflict("Prepare the investigation evidence before reviewing the note")
                if any(output["needs_review"] for output in state["outputs"].values()):
                    raise Conflict("Acknowledge affected stage outputs before reviewing the note")
                state["review"] = {"reviewed": True, "rationale": payload["rationale"], "prepared_note": None}
                state["current_stage"] = "human_review"
                record["rationale"] = payload["rationale"]
            elif command.action == "prepare_note":
                if not state["prepared"]:
                    raise Conflict("Prepare the investigation evidence before exporting a note")
                if not state["review"]["reviewed"]:
                    raise Conflict("Review the current note before preparing it")
                state["current_stage"] = "decision"
                state["review"]["prepared_note"] = self.note({**state, "revision": state["revision"] + 1})
            elif command.action == "request_clarification":
                if state["clarification"] and state["clarification"]["status"] == "pending":
                    raise Conflict("An investigation scope clarification is already pending")
                identity = uuid4().hex
                revision = state["revision"] + 1
                operations = build_scope_surface(identity, revision, SCOPE_QUESTION)
                validate_scope_surface(operations)
                state["clarification"] = {
                    "id": identity, "surface_revision": revision, "status": "pending",
                    "question": SCOPE_QUESTION, "operations": operations, "answer": None,
                }
            elif command.action in ("resolve_clarification", "cancel_clarification"):
                clarification = state["clarification"]
                if (not clarification or clarification["id"] != payload["clarification_id"]
                        or clarification["surface_revision"] != payload["surface_revision"]
                        or clarification["status"] != "pending"):
                    raise Conflict("Clarification is stale, cancelled, resolved or outside this session")
                if command.action == "resolve_clarification":
                    if not registry_fingerprint:
                        raise InvalidInput("Clarification response requires the server's extension registry")
                    answer = payload["answer"]
                    if len(answer.encode()) > 16384:
                        raise InvalidInput("Scope answer exceeds 16 KiB")
                    model = self.repo.settings.model(self.repo.get_chat(scope)["model_id"])
                    if not model or len(f"Investigation scope clarification:\n{answer}".encode()) > (model.context_budget_tokens - 2500) // 2:
                        raise InvalidInput("Scope answer exceeds the selected model's context budget")
                    clarification.update(status="resolved", answer=answer)
                    self.invalidate(state, list(STAGES))
                else:
                    clarification["status"] = "cancelled"
            sequence = self.save(connection, scope, state, record)
            receipt = {"chat_id": scope.chat_id, "revision": state["revision"], "sequence": sequence}
            if command.action == "prepare":
                receipt.update(self.queue(
                    connection, scope, state, command.client_request_id, "Prepare investigation using demo connector",
                    registry_fingerprint or "", "prepare",
                ))
            elif command.action == "resolve_clarification":
                receipt.update(self.queue(
                    connection, scope, state, command.client_request_id,
                    f"Investigation scope clarification:\n{payload['answer']}", registry_fingerprint or "",
                ))
            connection.execute(insert(investigation_commands).values(
                id=uuid4().hex, owner_id=scope.owner_id, chat_id=scope.chat_id, created=time.time(),
                client_request_id=command.client_request_id, request=body, receipt=receipt,
            ))
            return receipt
