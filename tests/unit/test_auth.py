from app.services.auth_service import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hashing_and_verification():
    plain = "SuperSecure@2026"
    hashed = hash_password(plain)

    # Hash should not be plain text
    assert hashed != plain
    assert "$" in hashed

    # Verify matching password
    assert verify_password(plain, hashed) is True

    # Reject incorrect password
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_creation_and_decoding():
    payload = {"sub": "42", "role": "admin"}
    token = create_access_token(payload)

    assert isinstance(token, str)
    assert len(token) > 20

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "42"
    assert decoded["role"] == "admin"


def test_invalid_jwt_token():
    assert decode_access_token("not.a.valid.jwt") is None
