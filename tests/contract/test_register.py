"""Contract tests for POST /auth/register."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success_returns_201_and_user_read(test_client: AsyncClient):
    response = await test_client.post(
        "/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "s3cur3P@ss!"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["name"] == "Alice"
    assert data["role"] == "user"
    assert "id" in data
    assert "created_at" in data
    # No password field, no is_active field
    assert "password" not in data
    assert "hashed_password" not in data
    assert "is_active" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(test_client: AsyncClient):
    payload = {"name": "Bob", "email": "bob@example.com", "password": "s3cur3P@ss!"}
    await test_client.post("/auth/register", json=payload)
    response = await test_client.post("/auth/register", json=payload)
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_register_case_insensitive_duplicate_returns_409(
    test_client: AsyncClient,
):
    """Re-registering with a different-case variant of the same email → 409."""
    await test_client.post(
        "/auth/register",
        json={"name": "Carol", "email": "carol@example.com", "password": "s3cur3P@ss!"},
    )
    response = await test_client.post(
        "/auth/register",
        json={"name": "Carol", "email": "Carol@Example.Com", "password": "s3cur3P@ss!"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_register_short_password_returns_422(test_client: AsyncClient):
    """Password of 7 characters → 422 VALIDATION_ERROR (lower boundary check FR-013)."""
    response = await test_client.post(
        "/auth/register",
        json={"name": "Dave", "email": "dave@example.com", "password": "short1!"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_register_long_password_returns_422(test_client: AsyncClient):
    """Password of 73 characters → 422 VALIDATION_ERROR
    (upper boundary check FR-013).
    """
    response = await test_client.post(
        "/auth/register",
        json={"name": "Eve", "email": "eve@example.com", "password": "A" * 73},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
