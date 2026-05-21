"""Unit tests for owner-scoped idempotency key derivation."""

from __future__ import annotations

from pydantic import SecretStr
from src.services.supplement_intake import derive_idempotency_key

_SECRET = SecretStr("unit-test-secret-not-used-anywhere-else")


def test_returns_none_for_blank_client_request_id() -> None:
    """Verify None and blank strings remain None — no idempotency key stored."""
    assert derive_idempotency_key(None, "owner-a", _SECRET) is None
    assert derive_idempotency_key("", "owner-a", _SECRET) is None
    assert derive_idempotency_key("   ", "owner-a", _SECRET) is None


def test_derived_key_has_owner_prefix() -> None:
    """Verify derived key carries a 16-hex prefix followed by the trimmed hint."""
    key = derive_idempotency_key("hint-1", "owner-a", _SECRET)
    assert key is not None
    prefix, _, hint = key.partition(":")
    assert len(prefix) == 16
    assert all(char in "0123456789abcdef" for char in prefix)
    assert hint == "hint-1"


def test_different_owners_get_different_prefixes() -> None:
    """Verify the prefix is owner-scoped — two users cannot collide."""
    key_a = derive_idempotency_key("dup", "owner-a", _SECRET)
    key_b = derive_idempotency_key("dup", "owner-b", _SECRET)
    assert key_a is not None
    assert key_b is not None
    assert key_a != key_b
    assert key_a.split(":")[0] != key_b.split(":")[0]


def test_same_owner_same_hint_yields_same_key() -> None:
    """Verify same owner + hint always produces the same derived key (idempotency)."""
    key_a = derive_idempotency_key("hint-9", "owner-x", _SECRET)
    key_b = derive_idempotency_key("hint-9", "owner-x", _SECRET)
    assert key_a == key_b


def test_long_hint_is_truncated() -> None:
    """Verify long client-supplied hints are truncated to 120 characters."""
    long_hint = "x" * 500
    key = derive_idempotency_key(long_hint, "owner-z", _SECRET)
    assert key is not None
    _, _, hint = key.partition(":")
    assert hint == "x" * 120
