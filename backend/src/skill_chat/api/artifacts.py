from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from skill_chat.api.dependencies import scope, service
from skill_chat.artifacts.service import CSP, ArtifactService

router = APIRouter()


@router.get("/api/chats/{chat_id}/artifacts/{version_id}/preview")
def preview(chat_id: str, version_id: str, request: Request):
    html = ArtifactService(service(request).repo).read_html(scope(request, chat_id), version_id)
    return HTMLResponse(
        html,
        headers={
            "Content-Security-Policy": CSP,
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
        },
    )


@router.get("/api/chats/{chat_id}/artifacts/{version_id}/download")
def download(chat_id: str, version_id: str, request: Request):
    html = ArtifactService(service(request).repo).read_html(scope(request, chat_id), version_id)
    return Response(
        html,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="presentation-{version_id}.html"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": CSP,
            "Cache-Control": "no-store",
        },
    )
