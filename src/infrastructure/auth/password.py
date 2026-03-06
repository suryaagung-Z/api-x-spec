"""Password hashing and verification utilities (bcrypt)."""
from __future__ import annotations

import bcrypt

# Pre-computed dummy hash used to keep verify_password timing constant even
# when the user is not found — prevents timing-based email enumeration.
_DUMMY_HASH: bytes = bcrypt.hashpw(b"dummy-timing-safe-path", bcrypt.gensalt(rounds=12))


def hash_password(plain: str, rounds: int = 12) -> str:
    """Return a bcrypt hash of *plain*."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=rounds)).decode()


def verify_password(plain: str, hashed: str | None) -> bool:
    """Return True if *plain* matches *hashed*.

    When *hashed* is None (unknown user), runs a dummy bcrypt check so that
    callers take approximately the same wall-clock time regardless of whether
    the user exists.
    """
    if hashed is None:
        # Timing-safe dummy path: always returns False
        bcrypt.checkpw(plain.encode(), _DUMMY_HASH)
        return False
    return bcrypt.checkpw(plain.encode(), hashed.encode())
