import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment BEFORE any app imports
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "true"
os.environ["DB_AUTO_CREATE"] = "false"
os.environ["SECRET_KEY"] = "test_secret_key_at_least_32_chars_long_for_validation"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["REQUIRE_API_KEY"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///test.db"


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine using SQLite."""
    from app.models import Base

    engine = create_engine("sqlite:///test.db", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    os.unlink("test.db") if os.path.exists("test.db") else None


@pytest.fixture
def db_session(engine):
    """Create a fresh database session for each test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(engine, db_session):
    """Create a test FastAPI client with database overrides."""
    from app.database import get_db
    from app.main import app

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_client_record(db_session):
    """Create a test client with API key for authenticated requests."""
    import secrets

    from app.models.client import Client
    from app.security import hash_api_key

    api_key = f"aiqso_seo_{secrets.token_urlsafe(32)}"
    client = Client(
        name="Test Client",
        email="test@example.com",
        api_key_hash=hash_api_key(api_key),
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return {"client": client, "api_key": api_key}


@pytest.fixture
def auth_headers(test_client_record):
    """Return headers with valid API key."""
    return {"X-API-Key": test_client_record["api_key"]}
