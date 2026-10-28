import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


class ModelChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    label: str = Field(min_length=1, max_length=100)
    provider: Literal["openai", "anthropic"]
    endpoint: str
    deployment: str = Field(min_length=1)
    scope: str = "https://ai.azure.com/.default"
    wire_api: Literal["responses", "completions"] = "responses"
    context_budget_tokens: int = Field(ge=4096, le=2_000_000)

    @model_validator(mode="after")
    def validate_endpoint(self):
        url = urlparse(self.endpoint)
        if url.scheme != "https" or not url.hostname or url.username or url.query or url.fragment:
            raise ValueError("Foundry endpoints must be HTTPS URLs without credentials, queries or fragments")
        suffix = "/anthropic" if self.provider == "anthropic" else "/openai/v1"
        if not url.path.rstrip("/").endswith(suffix):
            raise ValueError(f"{self.provider} endpoint must end in {suffix}")
        if not self.scope.startswith("https://") or not self.scope.endswith("/.default"):
            raise ValueError("Token scope must be an HTTPS /.default scope")
        return self


class Settings(BaseModel):
    models: tuple[ModelChoice, ...]
    default_model_id: str
    data_dir: Path
    project_dir: Path
    host: Literal["127.0.0.1", "localhost", "::1"] = "127.0.0.1"
    frontend_origin: str = "http://127.0.0.1:5173"
    remote_frontend_origin: str | None = None
    upload_limit_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    foreground_timeout_seconds: int = Field(default=120, gt=0)
    background_timeout_seconds: int = Field(default=1800, gt=0)
    classifier_timeout_seconds: int = Field(default=5, gt=0)
    pdf_page_limit: int = Field(default=500, gt=0)
    pdf_character_limit: int = Field(default=2_000_000, gt=0)
    pdf_timeout_seconds: int = Field(default=30, gt=0)
    webiq_api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)

    @field_validator("remote_frontend_origin")
    @classmethod
    def validate_remote_frontend_origin(cls, origin: str | None) -> str | None:
        if origin is None:
            return None
        url = urlparse(origin)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or "*" in url.hostname
            or url.username is not None
            or url.password is not None
            or url.path not in {"", "/"}
            or "?" in origin
            or "#" in origin
            or any(character.isspace() for character in origin)
        ):
            raise ValueError("Remote frontend must be an exact HTTP(S) origin without credentials or paths")
        if url.port is not None and url.port == 0:
            raise ValueError("Remote frontend port must be positive")
        return origin.rstrip("/")

    def model(self, model_id: str) -> ModelChoice | None:
        return next((choice for choice in self.models if choice.id == model_id), None)

    def public_models(self) -> list[dict[str, str]]:
        return [{"id": model.id, "label": model.label} for model in self.models]


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    if env is None:
        load_dotenv(Path(os.environ.get("APP_PROJECT_DIR", Path(__file__).resolve().parents[3])) / ".env")
    source = os.environ if env is None else env
    raw = source.get("APP_MODELS")
    if not raw:
        raise ValueError("APP_MODELS must contain a JSON array of configured Foundry model choices")
    models = tuple(ModelChoice.model_validate(entry) for entry in json.loads(raw))
    if not models or len({model.id for model in models}) != len(models):
        raise ValueError("APP_MODELS must contain nonempty, unique model IDs")
    default = source.get("APP_DEFAULT_MODEL_ID", models[0].id)
    if default not in {model.id for model in models}:
        raise ValueError("APP_DEFAULT_MODEL_ID is not configured")
    project = Path(source.get("APP_PROJECT_DIR", Path(__file__).resolve().parents[3])).resolve()
    origin = source.get("APP_FRONTEND_ORIGIN", "http://127.0.0.1:5173")
    if urlparse(origin).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Frontend origin must be loopback")
    options = {}
    for key in (
        "upload_limit_bytes",
        "foreground_timeout_seconds",
        "background_timeout_seconds",
        "classifier_timeout_seconds",
        "pdf_page_limit",
        "pdf_character_limit",
        "pdf_timeout_seconds",
    ):
        if f"APP_{key.upper()}" in source:
            options[key] = int(source[f"APP_{key.upper()}"])
    return Settings.model_validate(
        {
            "models": models,
            "default_model_id": default,
            "data_dir": Path(source.get("APP_DATA_DIR", str(project / ".data"))).resolve(),
            "project_dir": project,
            "host": source.get("APP_HOST", "127.0.0.1"),
            "frontend_origin": origin,
            "remote_frontend_origin": source.get("APP_REMOTE_FRONTEND_ORIGIN") or None,
            "webiq_api_key": source.get("WEBIQ_API_KEY", "").strip() or None,
            **options,
        }
    )
