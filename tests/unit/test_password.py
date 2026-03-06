"""Unit tests for hash_password / verify_password."""
from __future__ import annotations

from src.infrastructure.auth.password import hash_password, verify_password


def test_hash_differs_from_plain():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"


def test_verify_returns_true_for_correct_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed) is True


def test_verify_returns_false_for_wrong_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("wrong-password", hashed) is False


def test_verify_does_not_raise_for_none_hash():
    """Timing-safe dummy path: verify_password(plain, None) returns False
    without raising.
    """
    result = verify_password("any-password", None)
    assert result is False
