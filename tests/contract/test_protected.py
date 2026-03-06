"""Contract tests for GET /auth/me (protected endpoint)."""
from __future__ import annotations

import time

import jwt
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_me_with_valid_token_returns_200(
    test_client: AsyncClient, user_auth_headers: dict
):
    response = await test_client.get("/auth/me", headers=user_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "email" in data
    assert "password" not in data
    assert "is_active" not in data


@pytest.mark.asyncio
async def test_me_missing_authorization_header_returns_401(test_client: AsyncClient):
    response = await test_client.get("/auth/me")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


@pytest.mark.asyncio
async def test_me_malformed_token_returns_401(test_client: AsyncClient):
    response = await test_client.get(
        "/auth/me", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


@pytest.mark.asyncio
async def test_me_expired_token_returns_401(test_client: AsyncClient):
    """Token with exp in the past is rejected with 401."""
    expired_payload = {
        "sub": "00000000-0000-0000-0000-000000000000",
        "role": "user",
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,
    }
    token = jwt.encode(expired_payload, "test-secret", algorithm="HS256")
    response = await test_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


@pytest.mark.asyncio
async def test_me_tampered_token_returns_401(test_client: AsyncClient):
    """Token signed with a different secret is rejected with 401."""
    payload = {
        "sub": "some-user-id",
        "role": "user",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    tampered = jwt.encode(payload, "wrong-secret", algorithm="HS256")
    response = await test_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tampered}"}
    )
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers
