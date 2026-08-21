from app.utils.jwt import create_access_token, create_refresh_token, decode_token


def test_create_and_decode_access_token():
    token = create_access_token(subject="user-id-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-id-123"


def test_create_and_decode_refresh_token():
    token = create_refresh_token(subject="user-id-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-id-123"
    assert payload["type"] == "refresh"
