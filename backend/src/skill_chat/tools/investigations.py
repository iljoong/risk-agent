import json

from pydantic import Field

from skill_chat.contracts import Conflict, InvalidInput
from skill_chat.investigations.schemas import StrictModel
from skill_chat.investigations.service import InvestigationService
from skill_chat.storage.models import tasks, turns
from skill_chat.tools.context import ToolContext, ToolRegistration


class ReadInvestigation(StrictModel):
    character_offset: int = Field(default=0, ge=0)
    max_characters: int = Field(default=2000, ge=1, le=2000)


class ProposeOutput(StrictModel):
    expected_revision: int = Field(ge=1)
    stage_id: str = Field(pattern=r"^(investigate|gather_evidence|analyze|human_review)$")
    text: str = Field(min_length=1, max_length=12000)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)


def investigation_tools(repository) -> list[ToolRegistration]:
    service = InvestigationService(repository)

    async def read(arguments, context: ToolContext) -> str:
        request = ReadInvestigation.model_validate(arguments)
        state = service.get(context.scope)
        text = json.dumps({key: value for key, value in state.items() if key != "history"}, ensure_ascii=False)
        end = min(len(text), request.character_offset + request.max_characters)
        return json.dumps({
            "revision": state["revision"], "character_offset": request.character_offset,
            "text": text[request.character_offset:end],
            "next_offset": end if end < len(text) else None,
            "coverage": "Partial; continue with next_offset" if end < len(text) else "End of snapshot",
        })

    async def propose(arguments, context: ToolContext) -> str:
        request = ProposeOutput.model_validate(arguments)
        if not context.task_id:
            raise InvalidInput("Output proposals require a running background investigation task")
        task = repository.get(tasks, context.scope, context.task_id)
        if task["turn_id"] != context.run_id:
            raise InvalidInput("Output proposal does not belong to this execution")
        turn = repository.get(turns, context.scope, context.run_id)
        execution = turn["request"].get("investigation")
        if not execution or execution["operation"] != "agent":
            raise InvalidInput("This task is not an investigation agent run")
        if execution["base_revision"] != request.expected_revision:
            raise Conflict("Proposal revision does not match the execution snapshot")
        state = service.get(context.scope)
        permitted = {item["id"] for item in state["evidence"]}
        if not set(request.evidence_ids).issubset(permitted):
            raise InvalidInput("Output references unknown investigation evidence")
        service.stage_candidate(context.scope, context.task_id, request.expected_revision, {
            "output_updates": {request.stage_id: {"text": request.text, "evidence_ids": request.evidence_ids}},
        })
        return json.dumps({"status": "staged", "stage_id": request.stage_id,
                           "base_revision": request.expected_revision,
                           "notice": "Visible only if this task succeeds; human review is still required."})

    return [
        ToolRegistration("read_investigation", "Read this session's fictional investigation with bounded continuation.",
                         ReadInvestigation, read),
        ToolRegistration("propose_investigation_output", "Propose a cited draft stage update, published only on task success.",
                         ProposeOutput, propose),
    ]
