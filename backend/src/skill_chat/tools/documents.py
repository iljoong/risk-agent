import json

from pydantic import BaseModel, ConfigDict, Field

from skill_chat.contracts import InvalidInput
from skill_chat.documents.ingestion import AttachmentService
from skill_chat.storage.repository import Repository
from skill_chat.tools.context import ToolContext, ToolRegistration


class ReadDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attachment_id: str
    first_page: int = Field(default=1, ge=1)
    last_page: int = Field(default=5, ge=1)
    character_offset: int = Field(default=0, ge=0)
    max_characters: int = Field(default=2000, ge=1, le=2000)


def document_tools(repository: Repository) -> list[ToolRegistration]:
    async def read(arguments: BaseModel, context: ToolContext) -> str:
        args = ReadDocument.model_validate(arguments)
        if args.last_page < args.first_page or args.last_page - args.first_page > 19:
            raise InvalidInput("Read 1 to 20 pages at a time")
        item = AttachmentService(repository).get(context.scope, args.attachment_id)
        if item["state"] != "ready":
            raise InvalidInput("PDF is not ready for reading")
        pages = [page for page in item["pages"] if args.first_page <= page["number"] <= args.last_page]
        if not pages or args.character_offset > len(pages[0]["text"]):
            raise InvalidInput("PDF page range or character offset is outside the document")
        selected = []
        remaining = args.max_characters
        next_page = None
        for page in pages:
            start = args.character_offset if page["number"] == args.first_page else 0
            excerpt = page["text"][start : start + remaining]
            end = start + len(excerpt)
            selected.append(
                {
                    "number": page["number"],
                    "text": excerpt,
                    "character_offset": start,
                    "next_offset": end if end < len(page["text"]) else None,
                    "total_characters": len(page["text"]),
                }
            )
            remaining -= len(excerpt)
            if end < len(page["text"]):
                next_page = page["number"]
                break
            if remaining == 0:
                next_page = page["number"] + 1 if page["number"] < len(item["pages"]) else None
                break
        return json.dumps(
            {
                "filename": item["filename"],
                "pages": selected,
                "warnings": item["warnings"],
                "next_page": next_page,
                "coverage": "Partial" if next_page else "Requested range complete",
            },
            ensure_ascii=False,
        )

    return [
        ToolRegistration(
            "read_document",
            "Read bounded PDF text by attachment ID, page range and character_offset. Follow next_page/next_offset to read more.",
            ReadDocument,
            read,
        )
    ]
