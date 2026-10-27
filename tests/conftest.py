from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


PROJECT_DIR = Path(__file__).resolve().parent.parent
TEST_DB = PROJECT_DIR / "data" / "testlab-tests.db"
os.environ["TESTLAB_DB_PATH"] = str(TEST_DB)

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    if TEST_DB.exists():
        TEST_DB.unlink()
    with TestClient(app) as test_client:
        yield test_client
    for suffix in ("", "-shm", "-wal"):
        path = Path(f"{TEST_DB}{suffix}")
        if path.exists():
            path.unlink()


@pytest.fixture(scope="session")
def admin_token(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def customer_token(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": "customer", "password": "customer123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def guest_token(client: TestClient) -> str:
    response = client.post("/api/auth/guest")
    assert response.status_code == 200
    return response.json()["access_token"]

