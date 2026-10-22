import json

import pytest

from skill_chat.config import load_settings


def models():
    return [
        {
            "id": "openai",
            "label": "Proposal OpenAI",
            "provider": "openai",
            "endpoint": "https://example.openai.azure.com/openai/v1/",
            "deployment": "my-deployment",
            "wire_api": "responses",
            "context_budget_tokens": 16000,
        },
        {
            "id": "claude",
            "label": "Proposal Claude",
            "provider": "anthropic",
            "endpoint": "https://example.services.ai.azure.com/anthropic",
            "deployment": "my-claude",
            "context_budget_tokens": 16000,
        },
    ]


def test_config_rejects_duplicate_models_and_invalid_endpoints(tmp_path):
    for choices in ([models()[0], models()[0]], [{**models()[0], "endpoint": "http://evil.test"}]):
        with pytest.raises(ValueError):
            load_settings({"APP_MODELS": json.dumps(choices), "APP_DATA_DIR": str(tmp_path)})


def test_config_rejects_missing_default_and_nonlocal_host(tmp_path):
    for extra in ({"APP_DEFAULT_MODEL_ID": "missing"}, {"APP_HOST": "0.0.0.0"}):
        with pytest.raises(ValueError):
            load_settings({"APP_MODELS": json.dumps(models()), "APP_DATA_DIR": str(tmp_path), **extra})


def test_config_public_choices_do_not_expose_provider_details(tmp_path):
    settings = load_settings({"APP_MODELS": json.dumps(models()), "APP_DATA_DIR": str(tmp_path)})
    assert settings.public_models() == [
        {"id": "openai", "label": "Proposal OpenAI"},
        {"id": "claude", "label": "Proposal Claude"},
    ]
    assert settings.default_model_id == "openai"
    assert settings.model("unknown") is None


def test_webiq_key_is_optional_server_only_and_redacted(tmp_path):
    settings = load_settings({
        "APP_MODELS": json.dumps(models()), "APP_DATA_DIR": str(tmp_path),
        "WEBIQ_API_KEY": "private-webiq-key",
    })
    assert settings.webiq_api_key.get_secret_value() == "private-webiq-key"
    assert "private-webiq-key" not in repr(settings)
    assert "private-webiq-key" not in settings.model_dump_json()
