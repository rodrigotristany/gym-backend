import logging
import re
import uuid

from app.models.admin_user import AdminRole, AdminUser
from app.utils.password import hash_password


async def _make_admin(db_session, password="Str0ng!Pass", enabled=True):
    admin = AdminUser(
        email=f"admin-{uuid.uuid4()}@example.com",
        hashed_password=hash_password(password),
        role=AdminRole.admin,
        enabled=enabled,
    )
    db_session.add(admin)
    await db_session.flush()
    return admin


async def test_login_returns_tokens_for_valid_credentials(client, db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass")

    response = await client.post("/admin/auth/login", json={"email": admin.email, "password": "Str0ng!Pass"})

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_login_rejects_wrong_password(client, db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass")

    response = await client.post("/admin/auth/login", json={"email": admin.email, "password": "wrong"})

    assert response.status_code == 401


async def test_login_with_over_length_password_returns_401_not_500(client, db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass")

    response = await client.post(
        "/admin/auth/login", json={"email": admin.email, "password": "x" * 120}
    )

    assert response.status_code == 401


async def test_login_accepts_email_in_a_different_case(client, db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass")

    response = await client.post(
        "/admin/auth/login", json={"email": admin.email.upper(), "password": "Str0ng!Pass"}
    )

    assert response.status_code == 200


async def test_login_rejects_disabled_account(client, db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass", enabled=False)

    response = await client.post("/admin/auth/login", json={"email": admin.email, "password": "Str0ng!Pass"})

    assert response.status_code == 403


async def test_logout_revokes_refresh_token(client, db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass")
    login_response = await client.post(
        "/admin/auth/login", json={"email": admin.email, "password": "Str0ng!Pass"}
    )
    tokens = login_response.json()

    response = await client.post(
        "/admin/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200


async def test_logout_requires_authentication(client):
    # NOTE: the task brief's reference test expects 403 here (older FastAPI's
    # HTTPBearer default for a missing Authorization header). The installed
    # fastapi==0.141.1 (allowed by requirements.txt's `fastapi>=0.115,<1.0`)
    # changed HTTPBearer's auto_error to raise 401 instead. This is verified,
    # observed behavior of app.dependencies.get_current_admin (Task 6, out of
    # scope here) with no code change on our part — see task-8-report.md.
    response = await client.post("/admin/auth/logout", json={"refresh_token": "x"})
    assert response.status_code == 401


async def test_password_recovery_flow(client, db_session, caplog):
    admin = await _make_admin(db_session, password="Str0ng!Pass")

    with caplog.at_level(logging.INFO, logger="app.email"):
        request_response = await client.post(
            "/admin/auth/password-recovery/request", json={"email": admin.email}
        )
    assert request_response.status_code == 200
    code = re.search(r"code=(\d{6})", caplog.text).group(1)

    confirm_response = await client.post(
        "/admin/auth/password-recovery/confirm",
        json={"email": admin.email, "otp_code": code, "new_password": "weak"},
    )

    assert confirm_response.status_code == 200


async def test_password_recovery_confirm_rejects_over_length_password_with_400(client, db_session, caplog):
    admin = await _make_admin(db_session, password="Str0ng!Pass")

    with caplog.at_level(logging.INFO, logger="app.email"):
        await client.post("/admin/auth/password-recovery/request", json={"email": admin.email})
    code = re.search(r"code=(\d{6})", caplog.text).group(1)

    # Admins skip strength enforcement, so bcrypt's ValueError is the only guard
    # here — it must surface as a clean 400, not an unhandled 500.
    response = await client.post(
        "/admin/auth/password-recovery/confirm",
        json={"email": admin.email, "otp_code": code, "new_password": "x" * 100},
    )

    assert response.status_code == 400


async def test_password_recovery_request_is_silent_for_unknown_email(client):
    response = await client.post(
        "/admin/auth/password-recovery/request", json={"email": "nobody@example.com"}
    )
    assert response.status_code == 200
