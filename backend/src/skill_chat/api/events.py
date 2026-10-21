import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from skill_chat.api.dependencies import scope, service
from skill_chat.storage.models import turns

router = APIRouter()


@router.get("/api/chats/{chat_id}/turns/{turn_id}/events")
async def events(chat_id: str, turn_id: str, request: Request, after: int = 0):
    owner = scope(request, chat_id)
    app = service(request)
    app.repo.get(turns, owner, turn_id)
    last = max(after, int(request.headers.get("last-event-id", "0")))

    async def iterate():
        async for event in app.stream(owner, turn_id, last):
            yield f"id: {event['id']}\nevent: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"

    return StreamingResponse(
        iterate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
        },
    )
