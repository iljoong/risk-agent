from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel


class AppError(Exception):
    code = "invalid_input"
    status = 400


class NotFound(AppError):
    code = "not_found"
    status = 404


class Conflict(AppError):
    code = "conflict"
    status = 409


class InvalidInput(AppError):
    pass


class Unavailable(AppError):
    code = "unavailable"
    status = 503


@dataclass(frozen=True)
class Scope:
    owner_id: str
    chat_id: str


class ContextMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class AgentRequest:
    run_id: str
    scope: Scope
    model_id: str
    messages: tuple[ContextMessage, ...]
    skill_id: str | None = None
    task_id: str | None = None
    allow_tools: bool = True


class AgentEvent(BaseModel):
    type: Literal["text_delta", "stage", "tool_status", "artifact", "completed", "error", "promoted"]
    text: str = ""
    artifact_id: str | None = None


class Gateway(Protocol):
    def stream(self, request: AgentRequest) -> AsyncIterator[AgentEvent]: ...
    async def cancel(self, run_id: str) -> None: ...
