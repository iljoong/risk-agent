import re
import shutil
from pathlib import Path
from uuid import uuid4

from skill_chat.contracts import InvalidInput, Scope


class FileStore:
    def __init__(self, root: Path):
        self.root = root.resolve()

    @staticmethod
    def check(value: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", value):
            raise InvalidInput("Invalid storage identifier")
        return value

    def root_for(self, scope: Scope) -> Path:
        path = self.root / self.check(scope.owner_id) / self.check(scope.chat_id)
        if path.resolve() != path or not path.resolve().is_relative_to(self.root):
            raise InvalidInput("Storage path escapes managed data")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def resolve(self, scope: Scope, object_id: str) -> Path:
        base = self.root_for(scope)
        path = base / self.check(object_id)
        if path.resolve() != path or not path.resolve().is_relative_to(base):
            raise InvalidInput("Storage path escapes this chat")
        return path

    def write(self, scope: Scope, object_id: str, data: bytes) -> Path:
        target = self.resolve(scope, object_id)
        staged = self.resolve(scope, f"staged-{uuid4().hex}")
        staged.write_bytes(data)
        staged.replace(target)
        return target

    def delete_chat(self, scope: Scope):
        target = self.root_for(scope)
        # The exact owner/chat directory was resolved and checked above.
        shutil.rmtree(target)
