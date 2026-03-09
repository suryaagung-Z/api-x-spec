"""Contract tests for GET /admin/users (admin-only endpoint)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_users_with_admin_token_returns_200(
    test_client: AsyncClient, admin_auth_headers: dict
):
    response = await test_client.get("/admin/users", headers=admin_auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_admin_users_with_user_role_returns_403_no_www_authenticate(
    test_client: AsyncClient, user_auth_headers: dict
):
    response = await test_client.get("/admin/users", headers=user_auth_headers)
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"
    # 403 must NOT include WWW-Authenticate header (only 401 responses do)
    assert "WWW-Authenticate" not in response.headers


@pytest.mark.asyncio
async def test_admin_users_without_token_returns_401_with_www_authenticate(
    test_client: AsyncClient,
):
    response = await test_client.get("/admin/users")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers
