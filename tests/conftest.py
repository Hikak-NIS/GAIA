# ruff: noqa: E402 -- environment must precede application imports
import os
import tempfile
from pathlib import Path

TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix="gaia-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(TEST_DIRECTORY.name) / "gaia.db").as_posix()
os.environ["BACKGROUND_ENABLED"] = "false"
os.environ["WEB_ORIGIN"] = "http://localhost:5173"

import pytest
from fastapi.testclient import TestClient

from gaia.config import Base, engine
from gaia.main import app


@pytest.fixture(autouse=True)
def clean_database():
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


def register(client, *, name="Анна", email="anna@example.com", password="garden-pass-123"):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


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

