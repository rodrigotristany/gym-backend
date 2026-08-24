"""Cross-account-type isolation.

The auth stack is parameterized over ``user_type`` ("admin" | "user") and shares
one signing key, one ``refresh_tokens`` table and one service module between the
two account types. These tests pin down that the two types stay separated:
credentials, tokens and sessions belonging to one must never work against the
other.
"""

import uuid

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select

from app.dependencies import get_current_admin, get_current_user
from app.models.admin_user import AdminRole, AdminUser
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services import auth_service
from app.utils.hashing import sha256_hex
from app.utils.jwt import create_access_token, create_refresh_token
from app.utils.password import hash_password


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


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


async def _make_user(db_session, password="Str0ng!Pass", enabled=True):
    user = User(
        email=f"user-{uuid.uuid4()}@example.com",
        hashed_password=hash_password(password),
        enabled=enabled,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _is_revoked(db_session, refresh_token: str) -> bool:
    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == sha256_hex(refresh_token))
    )
    stored = result.scalar_one()
    return stored.revoked


# --- access tokens don't cross the admin/user boundary ----------------------


async def test_admin_access_token_is_rejected_by_get_current_user(db_session):
    admin = await _make_admin(db_session)
    token = create_access_token(subject=str(admin.id))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_bearer(token), db=db_session)
    assert exc_info.value.status_code == 401


async def test_user_access_token_is_rejected_by_get_current_admin(db_session):
    user = await _make_user(db_session)
    token = create_access_token(subject=str(user.id))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=_bearer(token), db=db_session)
    assert exc_info.value.status_code == 401


# --- refresh tokens are never accepted as bearer credentials ---------------


async def test_admin_refresh_token_is_rejected_by_both_dependencies(db_session):
    admin = await _make_admin(db_session)
    token = create_refresh_token(subject=str(admin.id))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=_bearer(token), db=db_session)
    assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_bearer(token), db=db_session)
    assert exc_info.value.status_code == 401


async def test_user_refresh_token_is_rejected_by_both_dependencies(db_session):
    user = await _make_user(db_session)
    token = create_refresh_token(subject=str(user.id))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_bearer(token), db=db_session)
    assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=_bearer(token), db=db_session)
    assert exc_info.value.status_code == 401


# --- logout can't revoke the other account type's session ------------------


async def test_admin_cannot_revoke_a_users_refresh_token(client, db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass")
    user = await _make_user(db_session, password="Str0ng!Pass")

    admin_tokens = (
        await client.post(
            "/admin/auth/login", json={"email": admin.email, "password": "Str0ng!Pass"}
        )
    ).json()
    user_tokens = (
        await client.post("/auth/login", json={"email": user.email, "password": "Str0ng!Pass"})
    ).json()

    response = await client.post(
        "/admin/auth/logout",
        json={"refresh_token": user_tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )

    # Silent no-op: 200, but the victim's session survives.
    assert response.status_code == 200
    assert await _is_revoked(db_session, user_tokens["refresh_token"]) is False


async def test_user_cannot_revoke_an_admins_refresh_token(client, db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass")
    user = await _make_user(db_session, password="Str0ng!Pass")

    admin_tokens = (
        await client.post(
            "/admin/auth/login", json={"email": admin.email, "password": "Str0ng!Pass"}
        )
    ).json()
    user_tokens = (
        await client.post("/auth/login", json={"email": user.email, "password": "Str0ng!Pass"})
    ).json()

    response = await client.post(
        "/auth/logout",
        json={"refresh_token": admin_tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {user_tokens['access_token']}"},
    )

    assert response.status_code == 200
    assert await _is_revoked(db_session, admin_tokens["refresh_token"]) is False


async def test_logout_still_revokes_the_callers_own_token(client, db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")
    tokens = (
        await client.post("/auth/login", json={"email": user.email, "password": "Str0ng!Pass"})
    ).json()

    response = await client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200
    assert await _is_revoked(db_session, tokens["refresh_token"]) is True


# --- authenticate() dispatches to the right table --------------------------


async def test_authenticate_as_admin_fails_for_a_user_account(db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")

    with pytest.raises(auth_service.AuthError) as exc_info:
        await auth_service.authenticate(db_session, "admin", user.email, "Str0ng!Pass")
    assert exc_info.value.status_code == 401


async def test_authenticate_as_user_fails_for_an_admin_account(db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass")

    with pytest.raises(auth_service.AuthError) as exc_info:
        await auth_service.authenticate(db_session, "user", admin.email, "Str0ng!Pass")
    assert exc_info.value.status_code == 401
