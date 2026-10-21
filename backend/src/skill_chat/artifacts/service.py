import time
from uuid import uuid4

import tinycss2
from bs4 import BeautifulSoup
from sqlalchemy import insert, select

from skill_chat.contracts import Conflict, InvalidInput, NotFound, Scope
from skill_chat.storage.models import artifacts, tasks
from skill_chat.storage.repository import Repository

CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; font-src 'none'; "
    "script-src 'none'; connect-src 'none'; frame-src 'none'; form-action 'none'; "
    "base-uri 'none'; sandbox"
)
TAGS = {
    "html",
    "head",
    "body",
    "title",
    "meta",
    "style",
    "main",
    "section",
    "article",
    "header",
    "footer",
    "aside",
    "nav",
    "div",
    "span",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "ul",
    "ol",
    "li",
    "dl",
    "dt",
    "dd",
    "strong",
    "em",
    "b",
    "i",
    "small",
    "br",
    "hr",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "blockquote",
    "pre",
    "code",
    "a",
    "sup",
    "sub",
}
ATTRIBUTES = {"class", "id", "style", "lang", "role", "aria-label", "charset", "name", "content", "href"}


def check_css(tokens):
    for token in tokens:
        if token.type in {"url", "error"}:
            raise InvalidInput("CSS URLs and invalid CSS are not allowed")
        if token.type == "at-keyword" and token.value.lower() not in {
            "media",
            "page",
            "keyframes",
            "supports",
        }:
            raise InvalidInput("External or unsupported CSS rules are not allowed")
        if token.type == "function":
            if token.lower_name in {"url", "image-set", "expression", "-webkit-image-set"}:
                raise InvalidInput("Active or external CSS is not allowed")
            check_css(token.arguments)
        if hasattr(token, "content") and token.content:
            check_css(token.content)
        if token.type == "ident" and token.value.lower() in {"behavior", "-moz-binding"}:
            raise InvalidInput("Active CSS is not allowed")


def validate_html(html: str) -> str:
    if not html.strip() or len(html.encode()) > 5 * 1024 * 1024:
        raise InvalidInput("HTML must be nonempty and no larger than 5 MiB")
    soup = BeautifulSoup(html, "html.parser")
    for element in soup.find_all(True):
        if element.name not in TAGS:
            raise InvalidInput(f"HTML element is not allowed: {element.name}")
        for name, value in element.attrs.items():
            if name not in ATTRIBUTES or name.startswith("on"):
                raise InvalidInput(f"HTML attribute is not allowed: {name}")
            if name == "href" and (not isinstance(value, str) or not value.startswith("#")):
                raise InvalidInput("Only in-document links are allowed")
            if name == "style":
                check_css(tinycss2.parse_component_value_list(str(value)))
        if element.name == "style":
            check_css(tinycss2.parse_component_value_list(element.get_text()))
    return soup.get_text(" ", strip=True)


class ArtifactService:
    def __init__(self, repository: Repository):
        self.repo = repository

    def publish(
        self,
        scope: Scope,
        run_id: str,
        task_id: str,
        html: str,
        title: str,
        parent_version_id: str | None = None,
    ) -> dict:
        text_content = validate_html(html)
        parent = self.get(scope, parent_version_id) if parent_version_id else None
        self.repo.get(tasks, scope, task_id)
        artifact_id = uuid4().hex
        data = {
            "id": artifact_id,
            "owner_id": scope.owner_id,
            "chat_id": scope.chat_id,
            "created": time.time(),
            "task_id": task_id,
            "turn_id": run_id,
            "title": title[:200],
            "parent_version_id": parent_version_id,
            "version": parent["version"] + 1 if parent else 1,
            "text_content": text_content,
            "state": "staged",
        }
        self.repo.files.write(scope, artifact_id, html.encode("utf-8"))
        with self.repo.db.transaction() as connection:
            current = (
                connection.execute(select(tasks).where(self.repo.owned(tasks, scope), tasks.c.id == task_id))
                .mappings()
                .first()
            )
            if not current or current["state"] != "running" or current["turn_id"] != run_id:
                raise Conflict("Artifact cannot be published by an inactive task")
            connection.execute(insert(artifacts).values(**data))
        return data

    def get(self, scope: Scope, version_id: str) -> dict:
        item = self.repo.get(artifacts, scope, version_id)
        if item["state"] != "published":
            raise NotFound("Artifact version is not complete")
        return item

    def read_html(self, scope: Scope, version_id: str) -> str:
        self.get(scope, version_id)
        return self.repo.files.resolve(scope, version_id).read_text(encoding="utf-8")
