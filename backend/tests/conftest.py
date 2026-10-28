"""
tests/conftest.py
Shared pytest fixtures: isolated in-memory test database + FastAPI TestClient.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, get_db
from main import app


@pytest.fixture()
def test_db():
    """
    Fresh in-memory SQLite database for each test.
    Fully isolated from the real Postgres database.

    StaticPool forces SQLAlchemy to reuse a single connection for this
    engine, instead of opening a new (empty) in-memory database per
    connection -- which is the default SQLite behavior and would make
    tables created in one request invisible to the next.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(test_db):
    """FastAPI TestClient wired to the isolated test database."""
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def registered_user(client):
    """Registers a test user and returns (email, password, access_token)."""
    email = "testuser@example.com"
    password = "testpass123"
    response = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"email": email, "password": password, "token": token}
