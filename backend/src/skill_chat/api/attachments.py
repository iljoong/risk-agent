from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile

from skill_chat.api.dependencies import scope, service
from skill_chat.contracts import InvalidInput
from skill_chat.documents.ingestion import AttachmentService

router = APIRouter()


@router.post("/api/chats/{chat_id}/attachments", status_code=201)
async def upload(chat_id: str, request: Request, file: Annotated[UploadFile, File()]):
    repo = service(request).repo
    try:
        data = await file.read(repo.settings.upload_limit_bytes + 1)
        if len(data) > repo.settings.upload_limit_bytes:
            raise InvalidInput("PDF exceeds the configured upload limit")
        return AttachmentService(repo).upload(scope(request, chat_id), file.filename or "upload.pdf", data)
    finally:
        await file.close()


@router.get("/api/chats/{chat_id}/attachments/{attachment_id}")
def status(chat_id: str, attachment_id: str, request: Request):
    return AttachmentService(service(request).repo).get(scope(request, chat_id), attachment_id)
