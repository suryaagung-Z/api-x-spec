"""JWT creation and decoding utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from src.infrastructure.config import settings

# Algorithm is hardcoded — NOT read from environment variables.
_ALGORITHM = "HS256"
_ALLOWED_ALGORITHMS = ["HS256"]


def create_access_token(sub: str, role: str) -> str:
    """Create a signed HS256 JWT carrying sub, role, iat, and exp claims."""
    now = datetime.now(tz=UTC)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": sub,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict[str, object]:
    """Decode and validate a JWT, returning the payload dict.

    Raises ``jwt.PyJWTError`` on invalid signature, expiry, or banned algorithm
    (``alg=none`` and any algorithm not in the explicit allowlist are rejected).
    """
    return dict(
        jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=_ALLOWED_ALGORITHMS,
        )
    )
