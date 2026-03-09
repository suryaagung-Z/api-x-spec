"""Contract tests for POST /auth/login."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success_returns_token_response(test_client: AsyncClient):
    await test_client.post(
        "/auth/register",
        json={"name": "Alice", "email": "alice@login.com", "password": "s3cur3P@ss!"},
    )
    response = await test_client.post(
        "/auth/login",
        json={"email": "alice@login.com", "password": "s3cur3P@ss!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401_with_www_authenticate(
    test_client: AsyncClient,
):
    await test_client.post(
        "/auth/register",
        json={"name": "Bob", "email": "bob@login.com", "password": "s3cur3P@ss!"},
    )
    response = await test_client.post(
        "/auth/login",
        json={"email": "bob@login.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert "WWW-Authenticate" in response.headers
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401_with_www_authenticate(
    test_client: AsyncClient,
):
    """Unknown email returns 401 with same message — no email enumeration."""
    response = await test_client.post(
        "/auth/login",
        json={"email": "nobody@login.com", "password": "s3cur3P@ss!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert "WWW-Authenticate" in response.headers
    assert response.headers["WWW-Authenticate"] == "Bearer"
