import multiprocessing
import time
from io import BytesIO
from uuid import uuid4

from pypdf import PdfReader
from pypdf.errors import PdfReadError, PdfStreamError
from sqlalchemy import insert

from skill_chat.config import Settings
from skill_chat.contracts import InvalidInput, Scope
from skill_chat.storage.models import attachments
from skill_chat.storage.repository import Repository


def validate_pdf(filename: str, content: bytes, settings: Settings) -> bytes:
    if not filename.lower().endswith(".pdf") or not content.startswith(b"%PDF-"):
        raise InvalidInput("Only PDF attachments are supported")
    if len(content) > settings.upload_limit_bytes:
        raise InvalidInput(f"PDF exceeds the {settings.upload_limit_bytes // (1024 * 1024)} MiB limit")
    return content


def extract_pdf(content: bytes, settings: Settings) -> dict:
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted:
            raise InvalidInput("Password-protected PDFs are not supported")
        if not reader.pages or len(reader.pages) > settings.pdf_page_limit:
            raise InvalidInput(f"PDF must contain 1 to {settings.pdf_page_limit} pages")
        pages, missing, total = [], [], 0
        for number, page in enumerate(reader.pages, 1):
            text = (page.extract_text() or "").strip()
            total += len(text)
            if total > settings.pdf_character_limit:
                raise InvalidInput("Extracted PDF text exceeds the configured limit")
            if not text:
                missing.append(number)
            pages.append({"number": number, "text": text})
        if total == 0:
            raise InvalidInput("This PDF has no extractable text. OCR is not supported")
        warnings = (
            [f"No extractable text on pages {', '.join(map(str, missing))}; analysis is incomplete"]
            if missing
            else []
        )
        return {"pages": pages, "missing_text_pages": missing, "warnings": warnings}
    except (PdfReadError, PdfStreamError, ValueError, KeyError, IndexError) as error:
        raise InvalidInput("Malformed or unsupported PDF") from error


def _extract_child(channel, content: bytes, settings: Settings):
    try:
        channel.send({"ok": extract_pdf(content, settings)})
    except InvalidInput as error:
        channel.send({"error": str(error)})
    finally:
        channel.close()


def extract_bounded(content: bytes, settings: Settings) -> dict:
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_extract_child, args=(sender, content, settings))
    process.start()
    sender.close()
    try:
        if not receiver.poll(settings.pdf_timeout_seconds):
            raise InvalidInput("PDF extraction timed out")
        try:
            result = receiver.recv()
        except EOFError as error:
            raise InvalidInput("PDF parser stopped unexpectedly") from error
        if "error" in result:
            raise InvalidInput(result["error"])
        return result["ok"]
    finally:
        if process.is_alive():
            process.terminate()
        process.join(timeout=5)
        receiver.close()
        process.close()


class AttachmentService:
    def __init__(self, repository: Repository):
        self.repo = repository

    def upload(self, scope: Scope, filename: str, content: bytes) -> dict:
        self.repo.get_chat(scope)
        validate_pdf(filename, content, self.repo.settings)
        attachment_id = uuid4().hex
        data = {
            "id": attachment_id,
            "owner_id": scope.owner_id,
            "chat_id": scope.chat_id,
            "created": time.time(),
            "filename": filename.replace("\\", "/").split("/")[-1][:200],
            "state": "pending",
            "pages": [],
            "warnings": [],
            "error": None,
        }
        self.repo.files.write(scope, attachment_id, content)
        with self.repo.db.transaction() as connection:
            connection.execute(insert(attachments).values(**data))
        return data

    def get(self, scope: Scope, attachment_id: str) -> dict:
        return self.repo.get(attachments, scope, attachment_id)

    def ingest(self, scope: Scope, attachment_id: str) -> dict:
        attachment = self.get(scope, attachment_id)
        if attachment["state"] == "ready":
            return attachment
        self.repo.change(attachments, scope, attachment_id, state="processing", error=None)
        try:
            result = extract_bounded(
                self.repo.files.resolve(scope, attachment_id).read_bytes(), self.repo.settings
            )
        except InvalidInput as error:
            self.repo.change(attachments, scope, attachment_id, state="failed", error=str(error))
            raise
        self.repo.change(
            attachments,
            scope,
            attachment_id,
            state="ready",
            pages=result["pages"],
            warnings=result["warnings"],
        )
        return self.get(scope, attachment_id)
