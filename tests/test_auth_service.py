import logging
import re
import uuid

import pytest
from sqlalchemy import select

from app.models.admin_user import AdminUser
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services import auth_service
from app.utils.password import hash_password, verify_password


async def _make_user(db_session, password="Str0ng!Pass", enabled=True):
    user = User(
        email=f"user-{uuid.uuid4()}@example.com",
        hashed_password=hash_password(password),
        enabled=enabled,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_authenticate_succeeds_with_correct_password(db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")
    result = await auth_service.authenticate(db_session, "user", user.email, "Str0ng!Pass")
    assert result.id == user.id


async def test_authenticate_rejects_wrong_password(db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")
    with pytest.raises(auth_service.AuthError) as exc_info:
        await auth_service.authenticate(db_session, "user", user.email, "wrong")
    assert exc_info.value.status_code == 401


async def test_authenticate_rejects_disabled_account(db_session):
    user = await _make_user(db_session, password="Str0ng!Pass", enabled=False)
    with pytest.raises(auth_service.AuthError) as exc_info:
        await auth_service.authenticate(db_session, "user", user.email, "Str0ng!Pass")
    assert exc_info.value.status_code == 403


async def test_issue_tokens_creates_refresh_token_row(db_session):
    user = await _make_user(db_session)
    tokens = await auth_service.issue_tokens(db_session, "user", user.id)
    assert tokens["token_type"] == "bearer"

    result = await db_session.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))
    assert result.scalar_one_or_none() is not None


async def test_refresh_access_token_rotates_and_revokes_old_token(db_session):
    user = await _make_user(db_session)
    tokens = await auth_service.issue_tokens(db_session, "user", user.id)

    new_tokens = await auth_service.refresh_access_token(db_session, tokens["refresh_token"])

    assert new_tokens["refresh_token"] != tokens["refresh_token"]
    with pytest.raises(auth_service.AuthError):
        await auth_service.refresh_access_token(db_session, tokens["refresh_token"])


async def test_revoke_refresh_token_prevents_reuse(db_session):
    user = await _make_user(db_session)
    tokens = await auth_service.issue_tokens(db_session, "user", user.id)

    await auth_service.revoke_refresh_token(db_session, "user", user.id, tokens["refresh_token"])

    with pytest.raises(auth_service.AuthError):
        await auth_service.refresh_access_token(db_session, tokens["refresh_token"])


async def test_revoke_refresh_token_ignores_another_principals_token(db_session):
    owner = await _make_user(db_session)
    other = await _make_user(db_session)
    tokens = await auth_service.issue_tokens(db_session, "user", owner.id)

    # Silent no-op: the token isn't the caller's, so it must stay usable.
    await auth_service.revoke_refresh_token(db_session, "user", other.id, tokens["refresh_token"])

    refreshed = await auth_service.refresh_access_token(db_session, tokens["refresh_token"])
    assert "access_token" in refreshed


async def test_revoke_refresh_token_ignores_wrong_user_type(db_session):
    user = await _make_user(db_session)
    tokens = await auth_service.issue_tokens(db_session, "user", user.id)

    await auth_service.revoke_refresh_token(db_session, "admin", user.id, tokens["refresh_token"])

    refreshed = await auth_service.refresh_access_token(db_session, tokens["refresh_token"])
    assert "access_token" in refreshed


async def test_create_and_verify_otp_roundtrip(db_session):
    user = await _make_user(db_session)
    code = await auth_service.create_otp(db_session, "user", user.id, "login_otp")
    await auth_service.verify_otp(db_session, "user", user.id, "login_otp", code)


async def test_create_otp_invalidates_previous_unused_codes(db_session):
    user = await _make_user(db_session)
    first = await auth_service.create_otp(db_session, "user", user.id, "login_otp")
    second = await auth_service.create_otp(db_session, "user", user.id, "login_otp")

    with pytest.raises(auth_service.AuthError):
        await auth_service.verify_otp(db_session, "user", user.id, "login_otp", first)

    await auth_service.verify_otp(db_session, "user", user.id, "login_otp", second)


async def test_create_otp_does_not_invalidate_other_purposes(db_session):
    user = await _make_user(db_session)
    recovery_code = await auth_service.create_otp(db_session, "user", user.id, "password_recovery")
    await auth_service.create_otp(db_session, "user", user.id, "login_otp")

    await auth_service.verify_otp(db_session, "user", user.id, "password_recovery", recovery_code)


async def test_verify_otp_rejects_wrong_code(db_session):
    user = await _make_user(db_session)
    await auth_service.create_otp(db_session, "user", user.id, "login_otp")
    with pytest.raises(auth_service.AuthError):
        await auth_service.verify_otp(db_session, "user", user.id, "login_otp", "000000")


async def test_verify_otp_rejects_reused_code(db_session):
    user = await _make_user(db_session)
    code = await auth_service.create_otp(db_session, "user", user.id, "login_otp")
    await auth_service.verify_otp(db_session, "user", user.id, "login_otp", code)
    with pytest.raises(auth_service.AuthError):
        await auth_service.verify_otp(db_session, "user", user.id, "login_otp", code)


async def test_register_creates_user_with_hashed_password(db_session):
    user = await auth_service.register(db_session, "newbie@example.com", "Str0ng!Pass")
    assert user.email == "newbie@example.com"
    assert verify_password("Str0ng!Pass", user.hashed_password) is True


async def test_register_rejects_weak_password(db_session):
    with pytest.raises(ValueError):
        await auth_service.register(db_session, "weak@example.com", "weak")


async def test_register_rejects_duplicate_email(db_session):
    user = await _make_user(db_session)
    with pytest.raises(auth_service.AuthError) as exc_info:
        await auth_service.register(db_session, user.email, "Str0ng!Pass")
    assert exc_info.value.status_code == 409


async def test_get_principal_by_email_returns_none_for_unknown_email(db_session):
    result = await auth_service.get_principal_by_email(db_session, "user", "nobody@example.com")
    assert result is None


async def test_get_principal_by_email_returns_the_matching_principal(db_session):
    user = await _make_user(db_session)
    result = await auth_service.get_principal_by_email(db_session, "user", user.email)
    assert result.id == user.id


async def test_request_password_recovery_is_silent_for_unknown_email(db_session):
    await auth_service.request_password_recovery(db_session, "user", "nobody@example.com")


async def test_confirm_password_recovery_updates_password(db_session, caplog):
    user = await _make_user(db_session, password="Str0ng!Pass")
    with caplog.at_level(logging.INFO, logger="app.email"):
        await auth_service.request_password_recovery(db_session, "user", user.email)
    code = re.search(r"code=(\d{6})", caplog.text).group(1)

    await auth_service.confirm_password_recovery(
        db_session, "user", user.email, code, "N3w!Passw0rd", enforce_strength=True
    )

    refreshed = await db_session.get(User, user.id)
    assert verify_password("N3w!Passw0rd", refreshed.hashed_password) is True


async def test_confirm_password_recovery_revokes_existing_refresh_tokens(db_session, caplog):
    user = await _make_user(db_session, password="Str0ng!Pass")
    tokens = await auth_service.issue_tokens(db_session, "user", user.id)

    with caplog.at_level(logging.INFO, logger="app.email"):
        await auth_service.request_password_recovery(db_session, "user", user.email)
    code = re.search(r"code=(\d{6})", caplog.text).group(1)

    await auth_service.confirm_password_recovery(
        db_session, "user", user.email, code, "N3w!Passw0rd", enforce_strength=True
    )

    result = await db_session.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))
    assert all(row.revoked for row in result.scalars().all())
    with pytest.raises(auth_service.AuthError):
        await auth_service.refresh_access_token(db_session, tokens["refresh_token"])


async def test_confirm_password_recovery_enforces_strength_before_consuming_otp(db_session, caplog):
    user = await _make_user(db_session, password="Str0ng!Pass")
    with caplog.at_level(logging.INFO, logger="app.email"):
        await auth_service.request_password_recovery(db_session, "user", user.email)
    code = re.search(r"code=(\d{6})", caplog.text).group(1)

    with pytest.raises(ValueError):
        await auth_service.confirm_password_recovery(
            db_session, "user", user.email, code, "weak", enforce_strength=True
        )

    # OTP must still be usable since the weak password was rejected before consuming it
    await auth_service.confirm_password_recovery(
        db_session, "user", user.email, code, "N3w!Passw0rd", enforce_strength=True
    )


async def test_confirm_password_recovery_skips_strength_for_admins(db_session, caplog):
    admin = AdminUser(email=f"admin-{uuid.uuid4()}@example.com", hashed_password=hash_password("Str0ng!Pass"))
    db_session.add(admin)
    await db_session.flush()

    with caplog.at_level(logging.INFO, logger="app.email"):
        await auth_service.request_password_recovery(db_session, "admin", admin.email)
    code = re.search(r"code=(\d{6})", caplog.text).group(1)

    await auth_service.confirm_password_recovery(
        db_session, "admin", admin.email, code, "weak", enforce_strength=False
    )

    refreshed = await db_session.get(AdminUser, admin.id)
    assert verify_password("weak", refreshed.hashed_password) is True
