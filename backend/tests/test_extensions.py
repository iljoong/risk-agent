import pytest

from skill_chat.contracts import InvalidInput
from skill_chat.extensions.registry import discover_extensions


def test_skill_discovery_validation_and_fingerprint(tmp_path):
    skills = tmp_path / "skills"
    directory = skills / "rfp-response"
    directory.mkdir(parents=True)
    file = directory / "SKILL.md"
    file.write_text(
        "---\nname: rfp-response\ndescription: Draft RFP slides\n---\nInstructions", encoding="utf-8"
    )
    registry = discover_extensions(skills, tmp_path / "tools")
    assert [skill.id for skill in registry.skills] == ["rfp-response"]
    before = registry.fingerprint
    file.write_text(file.read_text() + "\nMore instructions", encoding="utf-8")
    assert discover_extensions(skills, tmp_path / "tools").fingerprint != before
    with pytest.raises(InvalidInput):
        registry.get_skill("unknown")
    file.write_text("---\nname: other\ndescription: Bad\n---", encoding="utf-8")
    with pytest.raises(InvalidInput):
        discover_extensions(skills, tmp_path / "tools")
