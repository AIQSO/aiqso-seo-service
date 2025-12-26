import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _test_env():
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("DEBUG", "true")
    os.environ.setdefault("DB_AUTO_CREATE", "false")
    os.environ.setdefault("SECRET_KEY", "test_secret_key_please_override_in_real_envs")
    os.environ.setdefault("LOG_LEVEL", "CRITICAL")

    # Clear cached settings if imported elsewhere.
    try:
        from app.config import get_settings

        get_settings.cache_clear()
    except Exception:
        pass

    yield
