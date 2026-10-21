from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pydantic import BaseModel

from skill_chat.contracts import Scope


@dataclass(frozen=True)
class ToolContext:
    scope: Scope
    run_id: str
    task_id: str | None
    skill_id: str | None = None


@dataclass(frozen=True)
class ToolRegistration:
    name: str
    description: str
    arguments: type[BaseModel]
    handler: Callable[[BaseModel, ToolContext], Awaitable[str]]
