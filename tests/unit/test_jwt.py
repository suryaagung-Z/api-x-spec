"""Unit tests for JWT utilities."""

from __future__ import annotations

import time

import jwt as pyjwt
import pytest

from src.infrastructure.auth.jwt import create_access_token, decode_token


def test_create_access_token_encodes_sub_role_iat_exp():
    token = create_access_token(sub="user-123", role="user")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "user"
    assert "iat" in payload
    assert "exp" in payload


def test_decode_token_returns_payload():
    token = create_access_token(sub="user-456", role="admin")
    payload = decode_token(token)
    assert payload["sub"] == "user-456"
    assert payload["role"] == "admin"


def test_decode_expired_token_raises():
    expired_payload = {
        "sub": "user-789",
        "role": "user",
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600,
    }
    from src.infrastructure.config import settings

    token = pyjwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    with pytest.raises(pyjwt.PyJWTError):
        decode_token(token)


def test_decode_tampered_signature_raises():
    token = create_access_token(sub="user-000", role="user")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(pyjwt.PyJWTError):
        decode_token(tampered)


def test_alg_none_rejected():
    """Unsigned (alg=none) tokens must be rejected unconditionally."""
    payload = {
        "sub": "attacker",
        "role": "admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    # Craft an alg=none token manually (PyJWT rejects encoding with alg=none)
    import base64
    import json

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    none_token = f"{header.decode()}.{body.decode()}."
    with pytest.raises(pyjwt.PyJWTError):
        decode_token(none_token)
