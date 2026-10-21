import pytest

from skill_chat.contracts import Conflict, InvalidInput, NotFound, Scope
from skill_chat.storage.files import FileStore


def test_every_chat_query_is_owner_scoped(repository):
    chat = repository.create_chat("owner-a", "openai", "RFP")
    assert repository.list_chats("owner-b") == []
    with pytest.raises(NotFound):
        repository.get_chat(Scope("owner-b", chat["id"]))
    scope = Scope("owner-a", chat["id"])
    repository.rename_chat(scope, "Updated")
    assert repository.get_chat(scope)["title"] == "Updated"
    repository.delete_chat(scope)
    assert repository.list_chats("owner-a") == []


def test_managed_files_reject_traversal(settings):
    files = FileStore(settings.data_dir)
    scope = Scope("owner-a", "chat-a")
    with pytest.raises(InvalidInput):
        files.resolve(scope, "..\\outside")
    with pytest.raises(InvalidInput):
        files.root_for(Scope("..", "chat-a"))


def test_busy_chat_is_not_deleted(repository):
    chat = repository.create_chat("owner-a", "openai", "RFP")
    scope = Scope("owner-a", chat["id"])
    repository.create_turn(scope, {"client_request_id": "1", "message": "hello", "model_id": "openai"})
    with pytest.raises(Conflict):
        repository.delete_chat(scope)


def test_symlinks_cannot_redirect_a_chat_to_another_owner(repository):
    from skill_chat.contracts import InvalidInput, Scope

    first = repository.create_chat("a", "openai")
    other = repository.create_chat("b", "openai")
    victim = repository.files.root_for(Scope("b", other["id"]))
    parent = repository.settings.data_dir / "a"
    parent.mkdir(exist_ok=True)
    link = parent / first["id"]
    try:
        link.symlink_to(victim, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlink creation is unavailable: {type(error).__name__}")
    with pytest.raises(InvalidInput):
        repository.files.root_for(Scope("a", first["id"]))


def test_orphan_cleanup_is_scoped_and_preserves_records_and_inflight_writes(repository):
    import os
    import time
    from uuid import uuid4

    from test_documents import make_pdf

    from skill_chat.documents.ingestion import AttachmentService

    first = repository.create_chat("a", "openai")
    second = repository.create_chat("b", "openai")
    scope = Scope("a", first["id"])
    other = Scope("b", second["id"])
    attachment = AttachmentService(repository).upload(scope, "RFP.pdf", make_pdf())
    tracked = repository.files.resolve(scope, attachment["id"])
    orphan = repository.files.write(scope, uuid4().hex, b"unfinished")
    staging = repository.files.write(scope, "staged-" + uuid4().hex, b"unfinished")
    unrelated = repository.files.write(scope, "developer-note", b"leave alone")
    recent = repository.files.write(scope, uuid4().hex, b"just being written")
    other_file = repository.files.write(other, uuid4().hex, b"other owner's orphan")
    for file in (tracked, orphan, staging, unrelated, other_file):
        os.utime(file, (time.time() - 120, time.time() - 120))
    repository.cleanup_orphan_files(scope)
    assert not orphan.exists() and not staging.exists()
    assert tracked.exists() and recent.exists() and unrelated.exists() and other_file.exists()


def test_interrupted_delete_resumes_without_touching_another_owner(repository, settings, monkeypatch):
    from skill_chat.storage.repository import Repository

    first = repository.create_chat("a", "openai")
    second = repository.create_chat("b", "openai")
    scope = Scope("a", first["id"])
    other = Scope("b", second["id"])
    first_file = repository.files.write(scope, "content", b"first")
    second_file = repository.files.write(other, "content", b"second")

    def interrupted(_scope):
        raise OSError("Simulated cleanup interruption")

    monkeypatch.setattr(repository.files, "delete_chat", interrupted)
    with pytest.raises(OSError):
        repository.delete_chat(scope)
    reopened = Repository(settings)
    assert reopened.list_chats("a") == []
    assert not first_file.exists()
    assert second_file.read_bytes() == b"second"
    assert reopened.get_chat(other)["id"] == second["id"]
    reopened.db.engine.dispose()
