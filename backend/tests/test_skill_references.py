import json

import pytest
from pydantic import ValidationError

from skill_chat.contracts import AgentRequest, ContextMessage, InvalidInput, Scope
from skill_chat.extensions.registry import discover_extensions
from skill_chat.tools.context import ToolContext


def reference_registry(tmp_path):
    from skill_chat.tools.references import skill_reference_tools

    for name, text in (("alpha", "Synthetic company baseline. " * 120), ("beta", "Other company's data.")):
        directory = tmp_path / "skills" / name
        references = directory / "references"
        references.mkdir(parents=True)
        (directory / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Analyze proposal risks\n---\nRead company-profile.md.",
            encoding="utf-8",
        )
        (references / "company-profile.md").write_text(text, encoding="utf-8")
    registry = discover_extensions(tmp_path / "skills", tmp_path / "tools")
    registry.add_tools(skill_reference_tools(registry))
    return registry


async def test_bound_reference_reader_uses_selected_skill_and_continuation_offsets(tmp_path):
    registry = reference_registry(tmp_path)
    request = AgentRequest(
        "run",
        Scope("local", "chat"),
        "openai",
        (ContextMessage(role="user", content="Review our risks"),),
        skill_id="alpha",
    )
    tool = next(tool for tool in registry.bind_tools(request) if tool.name == "read_skill_reference")

    async def read(offset):
        result = await tool.invoke(arguments={"filename": "company-profile.md", "character_offset": offset})
        return json.loads("".join(content.text for content in result if content.type == "text"))

    first = await read(0)
    assert first["skill_id"] == "alpha"
    assert len(first["text"]) == 2000
    assert first["next_offset"] == 2000
    assert first["coverage"] == "Partial"
    last = await read(first["next_offset"])
    assert last["next_offset"] is None
    assert first["text"] + last["text"] == "Synthetic company baseline. " * 120
    assert "Other company's data." not in first["text"] + last["text"]


async def test_reference_reader_requires_a_selected_skill(tmp_path):
    registry = reference_registry(tmp_path)
    tool = next(tool for tool in registry.tools if tool.name == "read_skill_reference")
    arguments = tool.arguments.model_validate({"filename": "company-profile.md"})
    with pytest.raises(InvalidInput, match="selected skill"):
        await tool.handler(arguments, ToolContext(Scope("local", "chat"), "run", None))


@pytest.mark.parametrize(
    "overrides",
    [
        {"filename": "../company-profile.md"},
        {"filename": "..\\company-profile.md"},
        {"filename": "C:\\private.md"},
        {"skill_id": "beta"},
    ],
)
def test_reference_reader_rejects_path_and_skill_overrides(tmp_path, overrides):
    registry = reference_registry(tmp_path)
    tool = next(tool for tool in registry.tools if tool.name == "read_skill_reference")
    with pytest.raises(ValidationError):
        tool.arguments.model_validate({"filename": "company-profile.md", **overrides})


async def test_reference_reader_rejects_redirected_files(tmp_path):
    registry = reference_registry(tmp_path)
    source = tmp_path / "skills" / "alpha" / "references" / "company-profile.md"
    private = tmp_path / "private.md"
    private.write_text("Not a skill reference", encoding="utf-8")
    source.unlink()
    source.symlink_to(private)
    tool = next(tool for tool in registry.tools if tool.name == "read_skill_reference")
    arguments = tool.arguments.model_validate({"filename": "company-profile.md"})
    context = ToolContext(Scope("local", "chat"), "run", None, skill_id="alpha")
    with pytest.raises(InvalidInput, match="redirected"):
        await tool.handler(arguments, context)


@pytest.mark.parametrize(
    "arguments",
    [
        {"filename": "missing.md"},
        {"filename": "company-profile.md", "character_offset": 100_000},
    ],
)
async def test_reference_reader_surfaces_missing_files_and_invalid_offsets(tmp_path, arguments):
    registry = reference_registry(tmp_path)
    tool = next(tool for tool in registry.tools if tool.name == "read_skill_reference")
    context = ToolContext(Scope("local", "chat"), "run", None, skill_id="alpha")
    with pytest.raises(InvalidInput):
        await tool.handler(tool.arguments.model_validate(arguments), context)
