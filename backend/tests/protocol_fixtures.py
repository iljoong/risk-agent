"""Small streaming protocol fixtures at the model HTTP boundary."""

import json


def emit_protocol(handler):
    text = "Local runtime answer."
    if handler.path.endswith("/responses"):
        part = {"type": "output_text", "text": text, "annotations": []}
        message = {
            "id": "msg_local",
            "type": "message",
            "status": "completed",
            "role": "assistant",
            "content": [part],
        }
        response = {
            "id": "resp_local",
            "object": "response",
            "created_at": 1,
            "status": "completed",
            "model": "local-model",
            "output": [message],
            "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
        }
        events = [
            ("response.created", {"response": {**response, "status": "in_progress", "output": []}}),
            (
                "response.output_item.added",
                {"output_index": 0, "item": {**message, "status": "in_progress", "content": []}},
            ),
            (
                "response.content_part.added",
                {"item_id": "msg_local", "output_index": 0, "content_index": 0, "part": {**part, "text": ""}},
            ),
            (
                "response.output_text.delta",
                {"item_id": "msg_local", "output_index": 0, "content_index": 0, "delta": text},
            ),
            (
                "response.output_text.done",
                {"item_id": "msg_local", "output_index": 0, "content_index": 0, "text": text},
            ),
            (
                "response.content_part.done",
                {"item_id": "msg_local", "output_index": 0, "content_index": 0, "part": part},
            ),
            ("response.output_item.done", {"output_index": 0, "item": message}),
            ("response.completed", {"response": response}),
        ]
    elif handler.path.endswith("/messages"):
        events = [
            (
                "message_start",
                {
                    "message": {
                        "id": "msg_local",
                        "type": "message",
                        "role": "assistant",
                        "model": "local-model",
                        "content": [],
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {"input_tokens": 10, "output_tokens": 0},
                    }
                },
            ),
            ("content_block_start", {"index": 0, "content_block": {"type": "text", "text": ""}}),
            ("content_block_delta", {"index": 0, "delta": {"type": "text_delta", "text": text}}),
            ("content_block_stop", {"index": 0}),
            (
                "message_delta",
                {"delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"output_tokens": 4}},
            ),
            ("message_stop", {}),
        ]
    else:
        return False
    for index, (kind, content) in enumerate(events):
        data = {"type": kind, **content}
        if kind.startswith("response."):
            data["sequence_number"] = index
        handler.wfile.write((f"event: {kind}\ndata: " + json.dumps(data) + "\n\n").encode())
    handler.wfile.flush()
    handler.close_connection = True
    return True
