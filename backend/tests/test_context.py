from test_documents import make_pdf

from skill_chat.contracts import Scope
from skill_chat.documents.context import ContextBuilder
from skill_chat.documents.ingestion import AttachmentService
from skill_chat.storage.models import attachments


def test_context_uses_scoped_pdf_sources_and_preserves_user_instruction(repository, settings):
    chat = repository.create_chat("a", "openai")
    scope = Scope("a", chat["id"])
    service = AttachmentService(repository)
    pdf = service.upload(scope, "RFP.pdf", make_pdf())
    service.ingest(scope, pdf["id"])
    messages = ContextBuilder(repository).build(scope, "openai", "Explain encryption")
    assert messages[0].role == "system"
    assert messages[-1].role == "user"
    assert messages[-1].content == "Explain encryption"
    assert any("RFP.pdf, page 1" in message.content for message in messages)


def publish_large_artifact(repository):
    from test_tasks import setup_task

    from skill_chat.artifacts.service import ArtifactService

    scope, turn, task, tasks = setup_task(repository)
    tasks.claim_next("context-test")
    text = "General proposal information. " * 2000 + "Critical delivery milestone is amber."
    artifact = ArtifactService(repository).publish(
        scope, turn["id"], task["id"], f"<section><p>{text}</p></section>", "Large draft"
    )
    tasks.finish(scope, task["id"], "succeeded", "Draft saved")
    return scope, artifact, text


def test_large_artifact_uses_bounded_relevant_sections_instead_of_blocking_chat(repository, settings):
    scope, artifact, _ = publish_large_artifact(repository)
    messages = ContextBuilder(repository).build(
        scope, "openai", "What is the critical delivery milestone?", artifact["id"]
    )
    source = next(
        message.content for message in messages if message.content.startswith("UNTRUSTED SAVED ARTIFACT:")
    )
    assert "Critical delivery milestone is amber." in source
    assert artifact["id"] in source and "Version 1" in source
    assert "Partial" in source
    assert (
        sum(len(message.content.encode()) for message in messages)
        < settings.model("openai").context_budget_tokens
    )


def dense_document(repository):
    chat = repository.create_chat("a", "openai")
    scope = Scope("a", chat["id"])
    pdf = AttachmentService(repository).upload(scope, "Dense.pdf", make_pdf())
    text = "General requirements and proposed services. " * 1200 + "Critical milestone is amber."
    repository.change(attachments, scope, pdf["id"], state="ready", pages=[{"number": 1, "text": text}])
    return scope, pdf, text


def test_dense_pdf_page_is_chunked_and_metadata_survives_partial_retrieval(repository, settings):
    scope, pdf, _ = dense_document(repository)
    messages = ContextBuilder(repository).build(scope, "openai", "What is the critical milestone?")
    source = next(
        message.content for message in messages if message.content.startswith("UNTRUSTED PDF SOURCES:")
    )
    assert pdf["id"] in source and "Dense.pdf, page 1" in source
    assert "Critical milestone is amber." in source
    assert "Partial" in source
    assert (
        sum(len(message.content.encode()) for message in messages)
        < settings.model("openai").context_budget_tokens
    )


async def test_dense_page_tool_can_read_all_text_in_bounded_offsets(repository):
    import json

    from skill_chat.tools.context import ToolContext
    from skill_chat.tools.documents import ReadDocument, document_tools

    scope, pdf, original = dense_document(repository)
    tool = document_tools(repository)[0]
    context = ToolContext(scope, "context-test", None)
    result = await tool.handler(ReadDocument(attachment_id=pdf["id"], first_page=1, last_page=1), context)
    pieces = []
    while True:
        assert len(result.encode()) <= 24000
        page = json.loads(result)["pages"][0]
        pieces.append(page["text"])
        offset = page["next_offset"]
        if offset is None:
            break
        result = await tool.handler(
            ReadDocument(attachment_id=pdf["id"], first_page=1, last_page=1, character_offset=offset), context
        )
    assert "".join(pieces) == original


async def test_large_artifact_tool_can_read_bounded_offsets(repository):
    import json

    from skill_chat.tools.artifacts import ReadArtifact, artifact_tools
    from skill_chat.tools.context import ToolContext

    scope, artifact, original = publish_large_artifact(repository)
    tool = artifact_tools(repository)[0]
    context = ToolContext(scope, "context-test", None)
    result = await tool.handler(ReadArtifact(version_id=artifact["id"]), context)
    assert len(result.encode()) <= 24000
    piece = json.loads(result)
    assert piece["next_offset"] is not None
    tail_offset = len(original) - 100
    result = await tool.handler(
        ReadArtifact(version_id=artifact["id"], character_offset=tail_offset), context
    )
    assert "Critical delivery milestone is amber." in json.loads(result)["text"]
