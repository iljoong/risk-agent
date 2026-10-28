import pytest
from fastapi.testclient import TestClient
from test_api import AnswerGateway
from test_investigations import command, create_investigation

from skill_chat.api.app import create_app
from skill_chat.contracts import Conflict, Scope


@pytest.fixture
def client(settings):
    with TestClient(create_app(
        settings, AnswerGateway(), owner_resolver=lambda request: request.headers.get("x-owner", "a"),
    )) as client:
        yield client


def test_investigation_routes_create_amend_and_enforce_origin_and_scope(client):
    response = client.post("/api/investigations", json={"model_id": "openai", "client_request_id": "create"})
    assert response.status_code == 201
    chat_id = response.json()["chat_id"]
    path = f"/api/chats/{chat_id}/investigation"
    initial = client.get(path).json()
    assert initial["snapshot"]["connector"] == "demo"
    assert initial["sequence"] > 0
    assert client.get(path, headers={"x-owner": "b"}).status_code == 404
    body = {"client_request_id": "amend", "expected_revision": 1, "action": "amend_output",
            "payload": {"stage_id": "investigate", "text": "Permitted scope", "reason": "Narrow checks"}}
    assert client.post(f"{path}/actions", json=body, headers={"origin": "https://evil.example"}).status_code == 403
    accepted = client.post(f"{path}/actions", json=body)
    assert accepted.status_code == 200
    assert client.post(f"{path}/actions", json=body).json() == accepted.json()
    assert client.post(f"{path}/actions", json={**body, "client_request_id": "stale"}).status_code == 409
    assert client.get(f"{path}/events?after=999999").status_code == 409
    assert client.get(f"{path}/events?after=-1").status_code == 422
    summary = next(item for item in client.get("/api/chats").json() if item["id"] == chat_id)
    assert summary["investigation"]["case_id"] == "CASE-1041"
    assert client.get(f"/api/chats/{chat_id}").json()["investigation"] == summary["investigation"]


def test_snapshot_watermark_and_projection_replay_are_consistent_and_scoped(repository):
    from skill_chat.investigations.projection import InvestigationProjection

    service, scope = create_investigation(repository)
    projection = InvestigationProjection(repository)
    snapshot, cursor = projection.snapshot_with_watermark(scope)
    command(service, scope, "amend_fact", {
        "beneficiary_description": "Not observed in available history", "reason": "Correct interpretation",
    })
    frames = projection.read_ui_events(scope, cursor)
    assert len(frames) == 1
    assert frames[0]["id"] > cursor
    assert frames[0]["payload"]["type"] == "STATE_SNAPSHOT"
    assert frames[0]["payload"]["snapshot"]["revision"] == snapshot["revision"] + 1
    assert projection.read_ui_events(scope, frames[0]["id"]) == []
    assert repository.snapshot(scope)["turns"] == []
    other = service.create("a", "openai", "other")
    with pytest.raises(Conflict):
        projection.read_ui_events(Scope("a", other["chat_id"]), cursor)
    with pytest.raises(Conflict):
        projection.read_ui_events(scope, 999999)


def test_large_amendment_history_has_bounded_frames_and_scoped_revision_pages(client):
    import json

    chat_id = client.post("/api/investigations", json={"model_id": "openai", "client_request_id": "long-history"}).json()["chat_id"]
    path = f"/api/chats/{chat_id}/investigation"
    for index in range(25):
        response = client.post(f"{path}/actions", json={
            "client_request_id": f"edit-{index}", "expected_revision": index + 1, "action": "amend_output",
            "payload": {"stage_id": "analyze", "text": "界" * 11996 + f"{index:04}", "reason": "Correct interpretation"},
        })
        assert response.status_code == 200
    state = client.get(path).json()["snapshot"]
    assert len(state["history"]) <= 20
    assert all("before" not in record and "after" not in record for record in state["history"])
    from skill_chat.investigations.projection import InvestigationProjection
    repo = client.app.state.service.repo
    frames = InvestigationProjection(repo).read_ui_events(Scope("a", chat_id), 0)
    assert max(len(json.dumps(frame["payload"])) for frame in frames) < 2_000_000
    page = client.get(f"{path}/history").json()
    assert len(page["records"]) == 10
    assert page["records"][0]["after"].endswith("0024")
    older = client.get(f"{path}/history?before={page['next_before']}").json()
    assert older["records"][0]["revision"] < page["records"][-1]["revision"]
    assert client.get(f"{path}/history", headers={"x-owner": "b"}).status_code == 404
