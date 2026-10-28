import json

from skill_chat.contracts import InvalidInput

CATALOG_ID = "urn:rci:scope-clarification:v1"
SCOPE_QUESTION = "Which question should the investigation address, and which permitted evidence should it prioritize?"


def build_scope_surface(clarification_id: str, revision: int, question: str) -> list[dict]:
    return [
        {"version": "v0.9", "createSurface": {"surfaceId": clarification_id, "catalogId": CATALOG_ID}},
        {"version": "v0.9", "updateComponents": {"surfaceId": clarification_id, "components": [
            {"id": "root", "component": "Column", "children": ["question", "answer", "submit"]},
            {"id": "question", "component": "Text", "text": question},
            {"id": "answer", "component": "TextInput", "label": "Investigation scope", "value": {"path": "/answer"}},
            {"id": "submit-label", "component": "Text", "text": "Apply scope and ask agent"},
            {"id": "submit", "component": "Button", "child": "submit-label",
             "action": {"event": {"name": "submit_scope", "context": {"answer": {"path": "/answer"}}}}},
        ]}},
        {"version": "v0.9", "updateDataModel": {
            "surfaceId": clarification_id, "path": "/", "value": {"answer": "", "surfaceRevision": revision},
        }},
    ]


def validate_scope_surface(operations: list[dict]):
    pending: list[tuple[object, int]] = [(operations, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > 12:
            raise InvalidInput("Clarification surface exceeds the depth limit")
        if isinstance(value, dict):
            pending.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            if len(value) > 100:
                raise InvalidInput("Clarification surface exceeds the component limit")
            pending.extend((item, depth + 1) for item in value)
    if len(json.dumps(operations, ensure_ascii=False).encode()) > 65536:
        raise InvalidInput("Clarification surface exceeds 64 KiB")
    try:
        identity = operations[0]["createSurface"]["surfaceId"]
        question = operations[1]["updateComponents"]["components"][1]["text"]
        revision = operations[2]["updateDataModel"]["value"]["surfaceRevision"]
        if not isinstance(question, str) or len(question) > 2000 or not isinstance(revision, int):
            raise ValueError
        # This pilot accepts one complete, fixed catalog template, not arbitrary UI.
        if operations != build_scope_surface(identity, revision, question):
            raise ValueError
    except (IndexError, KeyError, TypeError, ValueError) as error:
        raise InvalidInput("Unsupported clarification operations, component, binding or action") from error
