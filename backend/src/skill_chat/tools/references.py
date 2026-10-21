import json
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from skill_chat.contracts import InvalidInput
from skill_chat.tools.context import ToolContext, ToolRegistration

if TYPE_CHECKING:
    from skill_chat.extensions.registry import ExtensionRegistry


class ReadSkillReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9_-]*\.md$")
    character_offset: int = Field(default=0, ge=0)
    max_characters: int = Field(default=2000, ge=1, le=2000)


def skill_reference_tools(registry: "ExtensionRegistry") -> list[ToolRegistration]:
    async def read(arguments: BaseModel, context: ToolContext) -> str:
        args = ReadSkillReference.model_validate(arguments)
        if not context.skill_id:
            raise InvalidInput("Reading references requires an explicitly selected skill")
        skill = registry.get_skill(context.skill_id)
        source = skill.directory / "references" / args.filename
        try:
            if source.resolve() != source:
                raise InvalidInput("Skill reference paths cannot be redirected")
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError, RuntimeError) as error:
            raise InvalidInput("Cannot read the selected skill reference") from error
        if args.character_offset > len(text):
            raise InvalidInput("Reference character offset is outside the document")
        excerpt = text[args.character_offset : args.character_offset + args.max_characters]
        end = args.character_offset + len(excerpt)
        return json.dumps(
            {
                "skill_id": skill.id,
                "filename": args.filename,
                "text": excerpt,
                "character_offset": args.character_offset,
                "total_characters": len(text),
                "next_offset": end if end < len(text) else None,
                "coverage": "Partial" if args.character_offset or end < len(text) else "Complete",
            },
            ensure_ascii=False,
        )

    return [
        ToolRegistration(
            "read_skill_reference",
            "Read a Markdown filename from the explicitly selected skill's references folder. "
            "Returns at most 2000 characters; follow next_offset using character_offset.",
            ReadSkillReference,
            read,
        )
    ]
