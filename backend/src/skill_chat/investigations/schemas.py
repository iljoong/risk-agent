from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

STAGES = ("detect", "investigate", "gather_evidence", "analyze", "human_review", "decision")
Stage = Literal["detect", "investigate", "gather_evidence", "analyze", "human_review", "decision"]
Action = Literal[
    "amend_output", "amend_fact", "acknowledge_stage", "select_stage", "review_note",
    "prepare_note", "prepare", "request_clarification", "resolve_clarification", "cancel_clarification",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InvestigationCommand(StrictModel):
    client_request_id: str = Field(min_length=1, max_length=100)
    expected_revision: int = Field(ge=1)
    action: Action
    payload: dict = Field(default_factory=dict)


class AmendOutput(StrictModel):
    stage_id: Stage
    text: str = Field(min_length=1, max_length=12000)
    reason: str = Field(min_length=1, max_length=2000)


class AmendFact(StrictModel):
    beneficiary_description: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=2000)


class SelectStage(StrictModel):
    stage_id: Stage


class ReviewNote(StrictModel):
    rationale: str = Field(min_length=1, max_length=4000)


class Empty(StrictModel):
    pass


class ClarificationIdentity(StrictModel):
    clarification_id: str = Field(min_length=1, max_length=100)
    surface_revision: int = Field(ge=1)


class ResolveClarification(ClarificationIdentity):
    answer: str = Field(min_length=1, max_length=16384)


class StageOutput(StrictModel):
    text: str = Field(max_length=12000)
    version: int = Field(ge=1)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    needs_review: bool = True


class InvestigationSnapshot(StrictModel):
    chat_id: str
    case_id: str
    connector: str
    revision: int
    current_stage: Stage
    original_alert: dict
    sources: list[dict] = Field(max_length=7)
    shared_facts: dict
    outputs: dict[str, StageOutput]
    history: list[dict]
    review: dict
    clarification: dict | None = None
    external_status: Literal["unconfirmed"] = "unconfirmed"
    prepared: bool = False
    transactions: list[dict] = Field(default_factory=list, max_length=100)
    evidence: list[dict] = Field(default_factory=list, max_length=20)
    calculations: dict = Field(default_factory=dict)
