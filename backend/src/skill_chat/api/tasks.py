from fastapi import APIRouter, Request

from skill_chat.api.dependencies import scope, service

router = APIRouter()


@router.get("/api/chats/{chat_id}/tasks/{task_id}")
def status(chat_id: str, task_id: str, request: Request):
    return service(request).tasks.get(scope(request, chat_id), task_id)


@router.post("/api/chats/{chat_id}/tasks/{task_id}/cancel")
def cancel(chat_id: str, task_id: str, request: Request):
    return service(request).tasks.request_cancel(scope(request, chat_id), task_id)


@router.post("/api/chats/{chat_id}/tasks/{task_id}/retry", status_code=202)
def retry(chat_id: str, task_id: str, request: Request):
    app = service(request)
    return app.tasks.retry(scope(request, chat_id), task_id, app.registry.fingerprint)
