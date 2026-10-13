"""Tests run against an in-memory SQLite database, never the real Postgres.
get_db is overridden so every request in a test uses the throwaway engine."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine("sqlite+pysqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def book(client):
    r = client.post("/api/books", json={"title": "The Pragmatic Programmer", "author": "Hunt and Thomas",
                                        "isbn": "978-0135957059", "genre": "Technology", "total_copies": 2})
    assert r.status_code == 201
    return r.json()
