"""Test-only provider and process entry points; not importable through production configuration."""

import asyncio
import json
import sys
from pathlib import Path

import uvicorn
from reportlab.pdfgen import canvas
from test_config import models

from skill_chat.api.app import create_app
from skill_chat.artifacts.service import ArtifactService
from skill_chat.config import load_settings
from skill_chat.contracts import AgentEvent, Unavailable
from skill_chat.extensions.registry import build_registry
from skill_chat.storage.repository import Repository
from skill_chat.tasks.worker import Worker

ROOT = Path(__file__).resolve().parents[2]


class TestProvider:
    def __init__(self, repo):
        self.repo = repo

    async def stream(self, request):
        question = request.messages[-1].content
        if "intent classifier" in request.messages[0].content:
            mode = (
                "background"
                if any(word in question.lower() for word in ("draft", "generate", "revise"))
                else "foreground"
            )
            yield AgentEvent(type="text_delta", text=json.dumps({"mode": mode}))
        elif "simulate provider failure" in question.lower():
            raise Unavailable("Test provider unavailable. Check model access.")
        elif "simulate unsafe markdown" in question.lower():
            yield AgentEvent(
                type="text_delta",
                text='<img src=x onerror="document.documentElement.dataset.unsafeExecuted=1">\n\n[Unsafe link](javascript:alert(1))',
            )
        elif request.allow_tools:
            for text in ("Reading requirements", "Drafting slides", "Checking evidence"):
                yield AgentEvent(type="stage", text=text)
                await asyncio.sleep(2 if "cancellable" in question.lower() else 0.4)
            html = (
                "<!doctype html><html><head><style>body{font-family:Arial;background:#f6f8f3;margin:0}"
                "section{padding:40px;background:#173b31;color:white;min-height:320px;margin:20px;"
                "border-radius:8px}h1{font-size:32px}p{line-height:1.8}</style></head><body>"
                "<section><p>Proposal draft</p><h1>A response built around your requirements</h1>"
                "<p>RFP.pdf, page 1: Encryption and a delivery plan are required.</p>"
                "<p>Needs confirmation: supplier certifications and delivery commitments.</p></section>"
                "<section><h1>Evidence gaps</h1><p>Needs confirmation: supporting compliance evidence.</p>"
                "<p>Source: RFP.pdf, page 1</p></section></body></html>"
            )
            ArtifactService(self.repo).publish(
                request.scope, request.run_id, request.task_id, html, "RFP response draft"
            )
            yield AgentEvent(
                type="text_delta", text="Your draft is ready. Needs confirmation: supplier certifications."
            )
        else:
            has_artifact = any(
                message.content.startswith("UNTRUSTED SAVED ARTIFACT:") for message in request.messages
            )
            answer = (
                ("The saved draft ", "(Version 1) needs supporting evidence. ", "Source: RFP.pdf, page 1.")
                if has_artifact
                else ("No saved artifact is present in this request.",)
            )
            for text in answer:
                yield AgentEvent(type="text_delta", text=text)
                await asyncio.sleep(0.05)
        yield AgentEvent(type="completed")

    async def cancel(self, run_id):
        pass


def settings():
    return load_settings(
        {
            "APP_MODELS": json.dumps(models()),
            "APP_DATA_DIR": sys.argv[2] if len(sys.argv) > 2 else str(ROOT / ".data" / "e2e"),
            "APP_PROJECT_DIR": str(ROOT),
            "APP_FRONTEND_ORIGIN": "http://127.0.0.1:18962",
        }
    )


async def worker():
    repo = Repository(settings())
    instance = Worker(repo, build_registry(repo), TestProvider(repo))
    while True:
        if not await instance.run_once():
            await asyncio.sleep(0.1)


if __name__ == "__main__":
    if sys.argv[1] == "worker":
        asyncio.run(worker())
    else:
        config = settings()
        config.data_dir.mkdir(parents=True, exist_ok=True)
        fixture = canvas.Canvas(str(config.data_dir / "RFP.pdf"))
        fixture.drawString(72, 720, "RFP requires encryption and a delivery plan.")
        fixture.showPage()
        fixture.save()
        repo = Repository(config)
        uvicorn.run(create_app(config, TestProvider(repo)), host="127.0.0.1", port=18961)
