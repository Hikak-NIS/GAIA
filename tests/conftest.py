# ruff: noqa: E402 -- environment must precede application imports
import os
import tempfile
from pathlib import Path
import uuid

TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix="gaia-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(TEST_DIRECTORY.name) / "gaia.db").as_posix()
os.environ["BACKGROUND_ENABLED"] = "false"
os.environ["WEB_ORIGIN"] = "http://localhost:5173"

import pytest
from fastapi.testclient import TestClient

from gaia.config import Base, engine, settings, SessionLocal
from gaia.main import app
from gaia import models
from gaia.services import mail

MAILBOX = {}


@pytest.fixture(autouse=True)
def clean_database(monkeypatch):
    MAILBOX.clear()
    monkeypatch.setattr(mail, "send_code", lambda address, code: MAILBOX.__setitem__(address, code))
    monkeypatch.setattr(settings, "legacy_simulation_enabled", True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(
        app,
        headers={"X-GAIA-Request": "1", "Origin": "http://localhost:5173"},
    ) as test_client:
        yield test_client


def register(client, *, name="Анна", email="anna@example.com", password="garden-pass-123", nickname=None):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "nickname": nickname or "test_" + uuid.uuid4().hex[:16],
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201, response.text
    return verify_challenge(client, response).json()


def verify_challenge(client, response):
    challenge_id = response.json()["challenge_id"]
    with SessionLocal() as db:
        email = db.get(models.User, db.get(models.EmailChallenge, challenge_id).user_id).email
    result = client.post("/api/v1/auth/verify-email", json={"challenge_id": challenge_id, "code": MAILBOX[email]})
    assert result.status_code == 200, result.text
    return result


def login(client, identifier, password="garden-pass-123"):
    response = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    assert response.status_code == 200, response.text
    return verify_challenge(client, response)


def territory(client, *, name="Мой двор"):
    response = client.post(
        "/api/v1/territories",
        json={
            "name": name,
            "description": "Тестовый участок",
            "latitude": 43.2389,
            "longitude": 76.8897,
            "area": 120,
            "timezone": "Asia/Almaty",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture(scope="session", autouse=True)
def close_test_database():
    yield
    engine.dispose()
    TEST_DIRECTORY.cleanup()
