"""Unit test untuk JWT dan password."""
import pytest
from services.auth.jwt_handler import create_access_token, decode_token
from services.auth.password import hash_password, verify_password


def test_jwt_encode_decode():
    token = create_access_token("user-123")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"


def test_invalid_token():
    assert decode_token("invalid.token.here") is None


def test_password_hash_verify():
    hashed = hash_password("password123")
    assert verify_password("password123", hashed)
    assert not verify_password("wrong", hashed)
