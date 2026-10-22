import json

from pydantic import BaseModel, ConfigDict, Field

from skill_chat.artifacts.service import ArtifactService
from skill_chat.contracts import InvalidInput
from skill_chat.storage.repository import Repository
from skill_chat.tools.context import ToolContext, ToolRegistration


class ReadArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: str
    character_offset: int = Field(default=0, ge=0)
    max_characters: int = Field(default=2000, ge=1, le=2000)


class PublishHtml(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    html: str = Field(min_length=1, max_length=5 * 1024 * 1024)
    parent_version_id: str | None = None


def artifact_tools(repository: Repository) -> list[ToolRegistration]:
    service = ArtifactService(repository)

    async def read(arguments: BaseModel, context: ToolContext) -> str:
        args = ReadArtifact.model_validate(arguments)
        item = service.get(context.scope, args.version_id)
        source = item["text_content"]
        if args.character_offset > len(source):
            raise InvalidInput("Artifact character offset is outside the saved text")
        text = source[args.character_offset : args.character_offset + args.max_characters]
        end = args.character_offset + len(text)
        return json.dumps(
            {
                "id": item["id"],
                "version": item["version"],
                "text": text,
                "character_offset": args.character_offset,
                "total_characters": len(source),
                "next_offset": end if end < len(source) else None,
                "coverage": "Partial" if end < len(source) or args.character_offset else "Complete",
            },
            ensure_ascii=False,
        )

    async def publish(arguments: BaseModel, context: ToolContext) -> str:
        args = PublishHtml.model_validate(arguments)
        if context.task_id is None:
            raise InvalidInput("HTML generation requires a background task")
        item = service.publish(
            context.scope,
            context.run_id,
            context.task_id,
            args.html,
            args.title,
            args.parent_version_id,
        )
        return json.dumps(
            {
                "artifact_id": item["id"],
                "version": item["version"],
                "status": "staged",
                "download_url": f"/api/chats/{context.scope.chat_id}/artifacts/{item['id']}/download",
            }
        )

    return [
        ToolRegistration(
            "read_artifact",
            "Read bounded saved artifact text by version ID and character_offset; follow next_offset for more.",
            ReadArtifact,
            read,
        ),
        ToolRegistration(
            "publish_html",
            "Stage a passive HTML report or slides; published only when the task succeeds.",
            PublishHtml,
            publish,
        ),
    ]
