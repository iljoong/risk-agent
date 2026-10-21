from fastapi import Request

from skill_chat.chat.service import ChatService
from skill_chat.contracts import Scope


def service(request: Request) -> ChatService:
    result = request.app.state.service
    if not isinstance(result, ChatService):
        raise TypeError("Application service is not configured")
    return result


def scope(request: Request, chat_id: str) -> Scope:
    return Scope(request.app.state.owner_resolver(request), chat_id)
