from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from skill_chat.api.dependencies import scope, service
from skill_chat.api.schemas import CreateChat, PatchChat, TurnRequest
from skill_chat.contracts import Unavailable

router = APIRouter()


@router.get("/api/models")
def models(request: Request):
    settings = service(request).repo.settings
    return {"models": settings.public_models(), "default_model_id": settings.default_model_id}


@router.get("/api/skills")
def skills(request: Request):
    return [
        {"id": s.id, "name": s.name, "description": s.description} for s in service(request).registry.skills
    ]


@router.get("/api/chats")
def chats(request: Request):
    return service(request).repo.list_chats(request.app.state.owner_resolver(request))


@router.post("/api/chats", status_code=201)
def create_chat(body: CreateChat, request: Request):
    repo = service(request).repo
    model_id = body.model_id or repo.settings.default_model_id
    if not repo.settings.model(model_id):
        raise Unavailable("Model is not configured")
    return repo.create_chat(request.app.state.owner_resolver(request), model_id, body.title)


@router.get("/api/chats/{chat_id}")
def chat(chat_id: str, request: Request):
    return service(request).repo.snapshot(scope(request, chat_id))


@router.patch("/api/chats/{chat_id}")
def patch_chat(chat_id: str, body: PatchChat, request: Request):
    repo = service(request).repo
    owner = scope(request, chat_id)
    current = repo.get_chat(owner)
    if body.model_id and not repo.settings.model(body.model_id):
        raise Unavailable("Model is not configured")
    return repo.rename_chat(owner, body.title or current["title"], body.model_id)


@router.delete("/api/chats/{chat_id}", status_code=204)
def delete_chat(chat_id: str, request: Request):
    service(request).repo.delete_chat(scope(request, chat_id))


@router.post("/api/chats/{chat_id}/turns")
async def submit_turn(chat_id: str, body: TurnRequest, request: Request):
    receipt = await service(request).submit(scope(request, chat_id), body.model_dump())
    return JSONResponse(receipt, status_code=202 if receipt["mode"] == "background" else 200)


@router.post("/api/chats/{chat_id}/turns/{turn_id}/cancel")
async def cancel_turn(chat_id: str, turn_id: str, request: Request):
    return await service(request).cancel_turn(scope(request, chat_id), turn_id)
