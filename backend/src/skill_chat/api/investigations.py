import asyncio
import json

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import StreamingResponse

from skill_chat.api.dependencies import scope, service
from skill_chat.api.schemas import CreateInvestigation
from skill_chat.contracts import InvalidInput
from skill_chat.investigations.projection import InvestigationProjection
from skill_chat.investigations.schemas import InvestigationCommand
from skill_chat.investigations.service import InvestigationService

router = APIRouter()


@router.post("/api/investigations", status_code=201)
def create_investigation(body: CreateInvestigation, request: Request):
    repo = service(request).repo
    return InvestigationService(repo).create(
        request.app.state.owner_resolver(request),
        body.model_id or repo.settings.default_model_id, body.client_request_id,
    )


@router.get("/api/alerts")
def alerts(request: Request):
    return {"alerts": InvestigationService(service(request).repo).alerts(request.app.state.owner_resolver(request))}


@router.post("/api/alerts/{alert_id}/investigation")
def open_alert(alert_id: str, body: CreateInvestigation, request: Request, response: Response):
    repo = service(request).repo
    result = InvestigationService(repo).open_alert(
        request.app.state.owner_resolver(request),
        body.model_id or repo.settings.default_model_id, alert_id, body.client_request_id,
    )
    response.status_code = 201 if result["created"] else 200
    return result


@router.get("/api/chats/{chat_id}/investigation")
def snapshot(chat_id: str, request: Request):
    state, sequence = InvestigationProjection(service(request).repo).snapshot_with_watermark(scope(request, chat_id))
    return {"snapshot": state, "sequence": sequence}


@router.post("/api/chats/{chat_id}/investigation/actions")
def action(chat_id: str, body: InvestigationCommand, request: Request):
    app = service(request)
    return InvestigationService(app.repo).apply(
        scope(request, chat_id), body, registry_fingerprint=app.registry.fingerprint,
    )


@router.get("/api/chats/{chat_id}/investigation/history")
def history(chat_id: str, request: Request, before: int | None = Query(default=None, gt=0),
            limit: int = Query(default=10, ge=1, le=10)):
    return InvestigationService(service(request).repo).history(scope(request, chat_id), before, limit)


@router.get("/api/chats/{chat_id}/investigation/events")
async def events(chat_id: str, request: Request, after: int = Query(default=0, ge=0)):
    owner = scope(request, chat_id)
    projection = InvestigationProjection(service(request).repo)
    raw = request.headers.get("last-event-id", "0")
    if not raw.isascii() or not raw.isdecimal() or len(raw) > 16:
        raise InvalidInput("Invalid investigation event cursor")
    cursor = max(after, int(raw))
    projection.read_ui_events(owner, cursor)

    async def iterate():
        nonlocal cursor
        while not await request.is_disconnected():
            frames = projection.read_ui_events(owner, cursor)
            for frame in frames:
                cursor = frame["id"]
                payload = frame["payload"]
                if payload["type"] == "STATE_SNAPSHOT":
                    payload = {**payload, "snapshot": projection.service.project(payload["snapshot"])}
                yield f"id: {cursor}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            if not frames:
                yield ": investigation heartbeat\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(iterate(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-store", "X-Accel-Buffering": "no",
    })
