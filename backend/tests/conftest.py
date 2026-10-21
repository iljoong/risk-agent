import json

import pytest
from test_config import models

from skill_chat.config import load_settings


@pytest.fixture
def settings(tmp_path):
    return load_settings({"APP_MODELS": json.dumps(models()), "APP_DATA_DIR": str(tmp_path)})


@pytest.fixture
def repository(settings):
    from skill_chat.storage.repository import Repository

    return Repository(settings)
