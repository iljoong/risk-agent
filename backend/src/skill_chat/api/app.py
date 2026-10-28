import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from starlette.middleware.trustedhost import TrustedHostMiddleware

from skill_chat.agents.gateway import AgentGateway
from skill_chat.api import artifacts, attachments, chats, events, investigations, tasks
from skill_chat.chat.service import ChatService
from skill_chat.config import Settings, load_settings
from skill_chat.contracts import AppError, Gateway
from skill_chat.extensions.registry import build_registry
from skill_chat.storage.models import worker_status
from skill_chat.storage.repository import Repository

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    gateway: Gateway | None = None,
    owner_resolver: Callable[[Request], str] | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    repo = Repository(settings)
    registry = build_registry(repo)
    actual_gateway = gateway or AgentGateway(settings, registry)
    chat = ChatService(repo, registry, actual_gateway)

    @asynccontextmanager
    async def lifespan(_app):
        chat.recover_foreground()
        try:
            yield
        finally:
            await chat.close()
            if isinstance(actual_gateway, AgentGateway):
                await actual_gateway.close()
            repo.db.engine.dispose()

    app = FastAPI(title="RCI Agent API", lifespan=lifespan)
    app.state.service = chat
    app.state.owner_resolver = owner_resolver or (lambda _request: "local")
    frontend_origins = [settings.frontend_origin]
    if settings.remote_frontend_origin:
        frontend_origins.append(settings.remote_frontend_origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=frontend_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["content-type", "last-event-id"],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "127.0.0.1",
            "localhost",
            "[::1]",
            *(["testserver"] if gateway else []),
        ],
    )

    @app.middleware("http")
    async def local_guard(request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and (
            origin is not None
            and origin not in frontend_origins
            or request.headers.get("sec-fetch-site") == "cross-site"
        ):
            return JSONResponse(
                {"code": "forbidden_origin", "message": "Request origin is not allowed"}, status_code=403
            )
        if gateway is None and request.client and request.client.host not in {"127.0.0.1", "::1"}:
            return JSONResponse(
                {"code": "local_only", "message": "This version only accepts local connections"},
                status_code=403,
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(AppError)
    async def application_error(_request, error: AppError):
        correlation = uuid4().hex
        logger.warning("Request %s failed: %s", correlation, error.code)
        return JSONResponse(
            {"code": error.code, "message": str(error), "correlation_id": correlation},
            status_code=error.status,
        )

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        with repo.db.engine.connect() as connection:
            heartbeat = connection.execute(select(func.max(worker_status.c.heartbeat))).scalar()
        worker_ready = heartbeat is not None and heartbeat > time.time() - 60
        return JSONResponse(
            {
                "status": "ready" if worker_ready else "worker_unavailable",
                "worker_ready": worker_ready,
                "registry": registry.fingerprint,
            },
            status_code=200 if worker_ready else 503,
        )

    for routes in (chats.router, attachments.router, tasks.router, artifacts.router, events.router, investigations.router):
        app.include_router(routes)
    return app
