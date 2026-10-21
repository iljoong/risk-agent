"""Exercise the real SDK/CLI against a local model HTTP boundary, never a cloud provider."""

import json
import os
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

import pytest
from copilot import CopilotClient
from protocol_fixtures import emit_protocol

from skill_chat.agents.gateway import AgentGateway, build_provider
from skill_chat.contracts import AgentRequest, ContextMessage, Scope, Unavailable


@contextmanager
def local_model(call_tool=False, reject_auth=False, reference_file=None, skill_id="rfp-response"):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            received.append(body)
            if reject_auth:
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(
                    b'{"error":{"type":"authentication_error","message":"Local fixture rejected token"}}'
                )
                self.wfile.flush()
                self.close_connection = True
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            if emit_protocol(self):
                return
            delta = {"role": "assistant", "content": "Local runtime answer."}
            finish = "stop"
            called = {
                call.get("function", {}).get("name")
                for message in body["messages"]
                for call in message.get("tool_calls", [])
            }
            names = {tool.get("function", {}).get("name") for tool in body.get("tools", [])}
            if call_tool and "publish_html" in names and "publish_html" not in called:
                if reference_file and "read_skill_reference" not in called:
                    name = "read_skill_reference"
                    arguments = {"filename": reference_file}
                elif "skill" in names and "skill" not in called:
                    name = "skill"
                    arguments = {"skill": skill_id}
                else:
                    name = "publish_html"
                    arguments = {
                        "title": "Runtime draft",
                        "html": "<section><h1>Local runtime draft</h1><p>Needs confirmation: evidence.</p></section>",
                    }
                delta = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": f"local-{name}",
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(arguments)},
                        }
                    ],
                }
                finish = "tool_calls"
            chunk = {
                "id": "local-chat",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "local-model",
                "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
            }
            self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
            chunk["choices"][0] = {"index": 0, "delta": {}, "finish_reason": finish}
            self.wfile.write(("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode())
            self.wfile.flush()
            self.close_connection = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], received
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.runtime
@pytest.mark.skipif(
    os.environ.get("APP_RUN_RUNTIME_TESTS") != "1", reason="Opt-in local SDK/CLI process integration"
)
@pytest.mark.parametrize("reject_auth", [False, True], ids=["success", "authentication-error"])
async def test_gateway_stops_its_native_client_after_each_turn(settings, monkeypatch, reject_auth):
    clients = []

    class TrackingClient(CopilotClient):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            clients.append(self)

    monkeypatch.setattr("skill_chat.agents.gateway.CopilotClient", TrackingClient)
    with local_model(reject_auth=reject_auth) as (port, requests):

        def provider(model, acquire):
            result = build_provider(model, acquire)
            result["base_url"] = f"http://127.0.0.1:{port}/v1"
            return result

        monkeypatch.setattr("skill_chat.agents.gateway.build_provider", provider)
        gateway = AgentGateway(settings)

        async def token():
            return "local-test-token"

        monkeypatch.setattr(gateway.credentials, "provider", lambda scope: token)
        request = AgentRequest(
            uuid4().hex,
            Scope("runtime-test", uuid4().hex),
            "claude",
            (ContextMessage(role="user", content="Say hello"),),
            allow_tools=False,
        )
        try:
            if reject_auth:
                with pytest.raises(Unavailable, match="Provider request failed"):
                    _ = [event async for event in gateway.stream(request)]
            else:
                output = [event async for event in gateway.stream(request)]
                assert "Local runtime answer." in "".join(event.text for event in output)
            assert requests
            assert len(clients) == 1
            with pytest.raises(RuntimeError, match="Client not connected"):
                await clients[0].get_status()
        finally:
            await gateway.close()
            for client in clients:
                await client.stop()


@pytest.mark.runtime
@pytest.mark.skipif(
    os.environ.get("APP_RUN_RUNTIME_TESTS") != "1", reason="Opt-in local SDK/CLI process integration"
)
@pytest.mark.parametrize(
    "model_id,wire_api", [("openai", "completions"), ("openai", "responses"), ("claude", None)]
)
async def test_real_agent_framework_and_copilot_cli_stream(settings, monkeypatch, model_id, wire_api):
    with local_model() as (port, requests):

        def provider(model, acquire):
            result = build_provider(model, acquire)
            result["base_url"] = f"http://127.0.0.1:{port}/v1"
            if wire_api:
                result["wire_api"] = wire_api
            return result

        monkeypatch.setattr("skill_chat.agents.gateway.build_provider", provider)
        gateway = AgentGateway(settings)

        async def token():
            return "local-test-token"

        monkeypatch.setattr(gateway.credentials, "provider", lambda scope: token)
        try:
            output = [
                event
                async for event in gateway.stream(
                    AgentRequest(
                        uuid4().hex,
                        Scope("runtime-test", uuid4().hex),
                        model_id,
                        (
                            ContextMessage(role="system", content="You are a local business assistant."),
                            ContextMessage(role="user", content="Say hello"),
                        ),
                        allow_tools=False,
                    )
                )
            ]
            assert "Local runtime answer." in "".join(event.text for event in output)
            assert requests
            assert not requests[0].get("tools")
            body = requests[0]
            system = (
                body.get("instructions") or body.get("system") or body.get("messages", [{}])[0].get("content")
            )
            assert "You are a local business assistant." in json.dumps(system)
        finally:
            await gateway.close()


@pytest.mark.runtime
@pytest.mark.skipif(
    os.environ.get("APP_RUN_RUNTIME_TESTS") != "1", reason="Opt-in local SDK/CLI process integration"
)
@pytest.mark.parametrize(
    "skill_id,reference_file,instruction",
    [
        ("rfp-response", None, "Never invent supporting evidence"),
        ("rfp_analysis", "company-profile.md", "Separate buyer requirements"),
    ],
)
async def test_real_runtime_executes_scoped_tool_and_loads_selected_skill(
    repository, settings, monkeypatch, skill_id, reference_file, instruction
):
    from test_documents import make_pdf

    from skill_chat.documents.ingestion import AttachmentService
    from skill_chat.extensions.registry import build_registry
    from skill_chat.tasks.service import TaskService
    from skill_chat.tasks.worker import Worker

    registry = build_registry(repository)
    chat = repository.create_chat("runtime-test", "openai")
    scope = Scope("runtime-test", chat["id"])
    attachment = AttachmentService(repository).upload(scope, "RFP.pdf", make_pdf())
    turn, _ = repository.create_turn(
        scope,
        {
            "client_request_id": uuid4().hex,
            "message": "Generate draft slides with the RFP response skill.",
            "model_id": "openai",
            "skill_id": skill_id,
            "attachment_ids": [attachment["id"]],
        },
    )
    tasks = TaskService(repository)
    task = tasks.enqueue(scope, turn["id"], "openai", skill_id, registry.fingerprint)
    with local_model(call_tool=True, reference_file=reference_file, skill_id=skill_id) as (port, requests):

        def provider(model, acquire):
            result = build_provider(model, acquire)
            result["base_url"] = f"http://127.0.0.1:{port}/v1"
            result["wire_api"] = "completions"
            return result

        monkeypatch.setattr("skill_chat.agents.gateway.build_provider", provider)
        gateway = AgentGateway(settings, registry)
        acquisitions = 0

        async def token():
            nonlocal acquisitions
            acquisitions += 1
            return f"local-test-token-{acquisitions}"

        monkeypatch.setattr(gateway.credentials, "provider", lambda scope: token)
        try:
            await Worker(repository, registry, gateway).run_once()
            assert tasks.get(scope, task["id"])["state"] == "succeeded", (
                tasks.get(scope, task["id"])["error"],
                [
                    [tool.get("function", {}).get("name") for tool in body.get("tools", [])]
                    for body in requests
                ],
                [
                    message
                    for body in requests
                    for message in body["messages"]
                    if message.get("role") == "tool"
                ],
                repository.read_events(scope, turn["id"], 0),
                [(body.get("stream"), body.get("model")) for body in requests],
            )
            assert repository.snapshot(scope)["artifacts"][0]["title"] == "Runtime draft"
            assert any(message.get("role") == "tool" for body in requests for message in body["messages"])
            assert instruction in json.dumps(requests[0])
            if reference_file:
                tool_results = [m for body in requests for m in body["messages"] if m.get("role") == "tool"]
                assert "Cedarbridge Digital Services" in json.dumps(tool_results)
            assert acquisitions >= 2
        finally:
            await gateway.close()
