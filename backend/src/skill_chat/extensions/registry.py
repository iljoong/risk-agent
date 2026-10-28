import hashlib
import importlib.util
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from agent_framework import FunctionTool

from skill_chat.contracts import AgentRequest, InvalidInput
from skill_chat.tools.context import ToolContext, ToolRegistration

NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class SkillDefinition:
    id: str
    name: str
    description: str
    directory: Path


@dataclass
class ExtensionRegistry:
    skills: tuple[SkillDefinition, ...]
    fingerprint: str
    tools: list[ToolRegistration] = field(default_factory=list)

    def get_skill(self, skill_id: str) -> SkillDefinition:
        for skill in self.skills:
            if skill.id == skill_id:
                return skill
        raise InvalidInput(f"Unknown skill: {skill_id}")

    def add_tools(self, registrations: list[ToolRegistration]):
        names = {tool.name for tool in self.tools}
        for tool in registrations:
            if not NAME.fullmatch(tool.name) or tool.name in names:
                raise InvalidInput(f"Invalid or duplicate tool: {tool.name}")
            names.add(tool.name)
            self.tools.append(tool)
        self.fingerprint = hashlib.sha256(
            (
                self.fingerprint
                + "".join(tool.name + str(tool.arguments.model_json_schema()) for tool in registrations)
            ).encode()
        ).hexdigest()

    def bind_tools(self, request: AgentRequest) -> list[FunctionTool]:
        context = ToolContext(request.scope, request.run_id, request.task_id, request.skill_id)

        def bind(registration: ToolRegistration):
            async def invoke(**kwargs: object) -> str:
                arguments = registration.arguments.model_validate(kwargs)
                return await registration.handler(arguments, context)

            return FunctionTool(
                name=registration.name,
                description=registration.description,
                input_model=registration.arguments,
                func=invoke,
            )

        return [bind(registration) for registration in self.tools]


def discover_extensions(skills_dir: Path, tools_dir: Path) -> ExtensionRegistry:
    digest = hashlib.sha256()
    skills = []
    for root in (skills_dir, tools_dir):
        if not root.exists():
            continue
        for file in sorted(root.rglob("*")):
            if file.is_symlink() or not file.resolve().is_relative_to(root.resolve()):
                raise InvalidInput("Extension paths cannot be symlinks or escape their folder")
            if file.is_file() and "__pycache__" not in file.parts:
                digest.update(str(file.relative_to(root)).encode())
                digest.update(file.read_bytes())
    if skills_dir.exists():
        for directory in sorted(skills_dir.iterdir()):
            if not directory.is_dir() or directory.name.startswith("."):
                continue
            file = directory / "SKILL.md"
            if not file.is_file():
                raise InvalidInput(f"Skill {directory.name} is missing SKILL.md")
            content = file.read_text(encoding="utf-8")
            parts = content.split("---", 2)
            try:
                meta = yaml.safe_load(parts[1]) if content.startswith("---") and len(parts) == 3 else None
            except yaml.YAMLError as error:
                raise InvalidInput(f"Invalid frontmatter: {directory.name}") from error
            if (
                not isinstance(meta, dict)
                or meta.get("name") != directory.name
                or not NAME.fullmatch(directory.name)
            ):
                raise InvalidInput(f"Skill name must match its directory: {directory.name}")
            description = meta.get("description")
            if not isinstance(description, str) or not description.strip():
                raise InvalidInput(f"Skill description is required: {directory.name}")
            skills.append(SkillDefinition(directory.name, directory.name, description, directory.resolve()))
    registry = ExtensionRegistry(tuple(skills), digest.hexdigest())
    if tools_dir.exists():
        for file in sorted(tools_dir.glob("*.py")):
            spec = importlib.util.spec_from_file_location(f"app_tools_{file.stem}", file)
            if spec is None or spec.loader is None:
                raise InvalidInput(f"Cannot load tool module: {file.name}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            exported = getattr(module, "TOOLS", None)
            if not isinstance(exported, tuple) or not all(isinstance(t, ToolRegistration) for t in exported):
                raise InvalidInput(f"{file.name} must export TOOLS: tuple[ToolRegistration, ...]")
            registry.add_tools(list(exported))
    return registry


def build_registry(repository) -> ExtensionRegistry:
    from skill_chat.tools.artifacts import artifact_tools
    from skill_chat.tools.documents import document_tools
    from skill_chat.tools.investigations import investigation_tools
    from skill_chat.tools.references import skill_reference_tools
    from skill_chat.tools.webiq import webiq_tools

    root = repository.settings.project_dir
    registry = discover_extensions(root / "skills", root / "tools")
    registry.add_tools(
        document_tools(repository)
        + artifact_tools(repository)
        + skill_reference_tools(registry)
        + webiq_tools(repository.settings)
        + investigation_tools(repository)
    )
    return registry
