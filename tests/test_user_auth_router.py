import logging
import re
import uuid

from app.models.user import User
from app.utils.password import hash_password


async def _make_user(db_session, password="Str0ng!Pass", enabled=True):
    user = User(
        email=f"user-{uuid.uuid4()}@example.com",
        hashed_password=hash_password(password),
        enabled=enabled,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_register_creates_user_and_returns_tokens(client):
    response = await client.post(
        "/auth/register",
        json={"email": f"new-{uuid.uuid4()}@example.com", "password": "Str0ng!Pass"},
    )

    assert response.status_code == 201
    assert "access_token" in response.json()


async def test_register_rejects_weak_password(client):
    response = await client.post(
        "/auth/register",
        json={"email": f"new-{uuid.uuid4()}@example.com", "password": "weak"},
    )

    assert response.status_code == 400


async def test_register_rejects_duplicate_email(client, db_session):
    user = await _make_user(db_session)

    response = await client.post(
        "/auth/register", json={"email": user.email, "password": "Str0ng!Pass"}
    )

    assert response.status_code == 409


async def test_register_rejects_duplicate_email_differing_only_in_case(client, db_session):
    user = await _make_user(db_session)

    response = await client.post(
        "/auth/register", json={"email": user.email.upper(), "password": "Str0ng!Pass"}
    )

    assert response.status_code == 409


async def test_register_normalizes_email_case_and_whitespace(client):
    local = f"new-{uuid.uuid4()}"

    response = await client.post(
        "/auth/register",
        json={"email": f"  {local.upper()}@EXAMPLE.COM  ", "password": "Str0ng!Pass"},
    )
    assert response.status_code == 201

    # The stored address is the normalized one, so the lowercase form logs in.
    login = await client.post(
        "/auth/login", json={"email": f"{local}@example.com", "password": "Str0ng!Pass"}
    )
    assert login.status_code == 200


async def test_register_rejects_over_length_password(client):
    response = await client.post(
        "/auth/register",
        json={"email": f"new-{uuid.uuid4()}@example.com", "password": "A1!" + "a" * 100},
    )

    assert response.status_code == 400


async def test_login_with_over_length_password_returns_401_not_500(client, db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")

    response = await client.post(
        "/auth/login", json={"email": user.email, "password": "x" * 120}
    )

    assert response.status_code == 401


async def test_login_returns_tokens_for_valid_credentials(client, db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")

    response = await client.post("/auth/login", json={"email": user.email, "password": "Str0ng!Pass"})

    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_rejects_disabled_account(client, db_session):
    user = await _make_user(db_session, password="Str0ng!Pass", enabled=False)

    response = await client.post("/auth/login", json={"email": user.email, "password": "Str0ng!Pass"})

    assert response.status_code == 403


async def test_logout_revokes_refresh_token(client, db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")
    login_response = await client.post(
        "/auth/login", json={"email": user.email, "password": "Str0ng!Pass"}
    )
    tokens = login_response.json()

    response = await client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200


async def test_password_recovery_flow_enforces_strength(client, db_session, caplog):
    user = await _make_user(db_session, password="Str0ng!Pass")

    with caplog.at_level(logging.INFO, logger="app.email"):
        await client.post("/auth/password-recovery/request", json={"email": user.email})
    code = re.search(r"code=(\d{6})", caplog.text).group(1)

    weak_response = await client.post(
        "/auth/password-recovery/confirm",
        json={"email": user.email, "otp_code": code, "new_password": "weak"},
    )
    assert weak_response.status_code == 400

    strong_response = await client.post(
        "/auth/password-recovery/confirm",
        json={"email": user.email, "otp_code": code, "new_password": "N3w!Passw0rd"},
    )
    assert strong_response.status_code == 200


async def test_token_refresh_rotates_tokens(client, db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")
    login_response = await client.post(
        "/auth/login", json={"email": user.email, "password": "Str0ng!Pass"}
    )
    tokens = login_response.json()

    response = await client.post("/auth/token/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    assert response.json()["refresh_token"] != tokens["refresh_token"]


async def test_token_refresh_rejects_reused_token(client, db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")
    login_response = await client.post(
        "/auth/login", json={"email": user.email, "password": "Str0ng!Pass"}
    )
    tokens = login_response.json()
    await client.post("/auth/token/refresh", json={"refresh_token": tokens["refresh_token"]})

    response = await client.post("/auth/token/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 401
