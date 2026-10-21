from io import BytesIO

import pytest
from reportlab.pdfgen import canvas

from skill_chat.contracts import InvalidInput, NotFound, Scope
from skill_chat.documents.ingestion import AttachmentService, extract_pdf, validate_pdf


def make_pdf(blank_second=False):
    out = BytesIO()
    doc = canvas.Canvas(out)
    doc.drawString(72, 720, "RFP requires encryption and a delivery plan.")
    doc.showPage()
    if blank_second:
        doc.showPage()
    doc.save()
    return out.getvalue()


def test_mixed_pages_warn_and_sources_remain_page_numbered(settings):
    result = extract_pdf(validate_pdf("RFP.pdf", make_pdf(True), settings), settings)
    assert result["pages"][0]["number"] == 1
    assert result["missing_text_pages"] == [2]
    assert result["warnings"]


def test_non_pdf_oversize_and_malformed_input_rejected(settings):
    for filename, data in (("x.docx", b"%PDF-"), ("x.pdf", b"not pdf"), ("x.pdf", b"%PDF-broken")):
        with pytest.raises(InvalidInput):
            extract_pdf(validate_pdf(filename, data, settings), settings)
    limited = settings.model_copy(update={"upload_limit_bytes": 5})
    with pytest.raises(InvalidInput):
        validate_pdf("x.pdf", b"%PDF-1", limited)


def test_attachment_is_scoped_and_persists_extracted_pages(repository, settings):
    chat = repository.create_chat("a", "openai")
    scope = Scope("a", chat["id"])
    service = AttachmentService(repository)
    attachment = service.upload(scope, "RFP.pdf", make_pdf())
    service.ingest(scope, attachment["id"])
    assert service.get(scope, attachment["id"])["state"] == "ready"
    with pytest.raises(NotFound):
        service.get(Scope("b", chat["id"]), attachment["id"])


def test_encrypted_and_scanned_only_pdfs_fail_with_actionable_errors(settings):
    from pypdf import PdfWriter

    encrypted = PdfWriter()
    encrypted.add_blank_page(width=600, height=800)
    encrypted.encrypt("password")
    output = BytesIO()
    encrypted.write(output)
    with pytest.raises(InvalidInput, match="Password-protected"):
        extract_pdf(output.getvalue(), settings)
    scanned = PdfWriter()
    scanned.add_blank_page(width=600, height=800)
    output = BytesIO()
    scanned.write(output)
    with pytest.raises(InvalidInput, match="no extractable text"):
        extract_pdf(output.getvalue(), settings)


def test_pdf_extraction_timeout_terminates_its_parser_process(settings):
    import multiprocessing
    import time

    from skill_chat.documents.ingestion import extract_bounded

    existing = {process.pid for process in multiprocessing.active_children()}
    limited = settings.model_copy(update={"pdf_timeout_seconds": 0.001})
    started = time.monotonic()
    with pytest.raises(InvalidInput, match="timed out"):
        extract_bounded(make_pdf(), limited)
    assert time.monotonic() - started < 6
    assert {process.pid for process in multiprocessing.active_children()} == existing
