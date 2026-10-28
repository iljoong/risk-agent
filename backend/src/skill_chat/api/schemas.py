from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateChat(Input):
    title: str = Field(default="New chat", min_length=1, max_length=200)
    model_id: str | None = None


class PatchChat(Input):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    model_id: str | None = None


class CreateInvestigation(Input):
    client_request_id: str = Field(min_length=1, max_length=100)
    model_id: str | None = None


class TurnRequest(Input):
    client_request_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=100_000)
    model_id: str
    attachment_ids: list[str] = Field(default_factory=list, max_length=20)
    skill_id: str | None = None
    artifact_version_id: str | None = None
