import pytest
from fastapi.testclient import TestClient
from test_documents import make_pdf

from skill_chat.api.app import create_app
from skill_chat.contracts import AgentEvent


class AnswerGateway:
    async def stream(self, request):
        if "intent classifier" in request.messages[0].content:
            yield AgentEvent(type="text_delta", text='{"mode":"foreground"}')
        else:
            yield AgentEvent(type="text_delta", text="The saved draft needs supporting evidence.")
        yield AgentEvent(type="completed")

    async def cancel(self, run_id):
        pass


@pytest.fixture
def client(settings):
    app = create_app(
        settings, AnswerGateway(), owner_resolver=lambda request: request.headers.get("x-owner", "a")
    )
    with TestClient(app) as client:
        yield client


def new_chat(client):
    response = client.post("/api/chats", json={"model_id": "openai", "title": "RFP"})
    assert response.status_code == 201
    return response.json()["id"]


def test_short_question_streams_once_and_persists(client):
    chat = new_chat(client)
    body = {"client_request_id": "one", "message": "What is an RFP?", "model_id": "openai"}
    response = client.post(f"/api/chats/{chat}/turns", json=body)
    assert response.status_code == 200
    receipt = response.json()
    streamed = client.get(receipt["events_url"])
    assert "text_delta" in streamed.text
    assert "The saved draft" in streamed.text
    repeat = client.post(f"/api/chats/{chat}/turns", json=body)
    assert repeat.json()["turn_id"] == receipt["turn_id"]
    assert len(client.get(f"/api/chats/{chat}").json()["turns"]) == 1


def test_cross_owner_and_origin_are_rejected(client):
    chat = new_chat(client)
    assert client.get(f"/api/chats/{chat}", headers={"x-owner": "b"}).status_code == 404
    assert client.post("/api/chats", json={}, headers={"origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/chats", json={"owner_id": "b"}).status_code == 422


def test_pdf_submission_is_queued_and_busy_chat_returns_conflict(client):
    chat = new_chat(client)
    attached = client.post(
        f"/api/chats/{chat}/attachments", files={"file": ("RFP.pdf", make_pdf(), "application/pdf")}
    )
    assert attached.status_code == 201
    body = {
        "client_request_id": "one",
        "message": "Analyze this",
        "model_id": "openai",
        "attachment_ids": [attached.json()["id"]],
    }
    response = client.post(f"/api/chats/{chat}/turns", json=body)
    assert response.status_code == 202
    assert response.json()["task_id"]
    assert (
        client.post(f"/api/chats/{chat}/turns", json={**body, "client_request_id": "two"}).status_code == 409
    )
    assert client.delete(f"/api/chats/{chat}").status_code == 409
    cancelled = client.post(f"/api/chats/{chat}/tasks/{response.json()['task_id']}/cancel")
    assert cancelled.json()["state"] == "cancelled"


def test_invalid_model_and_unknown_skill_do_not_fallback(client):
    chat = new_chat(client)
    for extra in ({"model_id": "removed"}, {"model_id": "openai", "skill_id": "unknown"}):
        response = client.post(
            f"/api/chats/{chat}/turns",
            json={
                "client_request_id": "x",
                "message": "hello",
                **extra,
            },
        )
        assert response.status_code in (400, 503)
    assert client.get(f"/api/chats/{chat}").json()["turns"] == []


def test_child_routes_do_not_leak_another_owner_or_chat(client):
    chat = new_chat(client)
    other_chat = new_chat(client)
    attachment = client.post(
        f"/api/chats/{chat}/attachments", files={"file": ("RFP.pdf", make_pdf(), "application/pdf")}
    ).json()
    receipt = client.post(
        f"/api/chats/{chat}/turns",
        json={
            "client_request_id": "scoped",
            "message": "Analyze this",
            "model_id": "openai",
            "attachment_ids": [attachment["id"]],
        },
    ).json()
    for forbidden_chat, headers in ((chat, {"x-owner": "b"}), (other_chat, {})):
        prefix = f"/api/chats/{forbidden_chat}"
        assert client.get(f"{prefix}/attachments/{attachment['id']}", headers=headers).status_code == 404
        assert client.get(f"{prefix}/tasks/{receipt['task_id']}", headers=headers).status_code == 404
        assert client.post(f"{prefix}/tasks/{receipt['task_id']}/cancel", headers=headers).status_code == 404
        assert client.post(f"{prefix}/tasks/{receipt['task_id']}/retry", headers=headers).status_code == 404
        assert client.get(f"{prefix}/turns/{receipt['turn_id']}/events", headers=headers).status_code == 404
