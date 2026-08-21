import uuid

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies import get_current_admin, get_current_user
from app.models.admin_user import AdminRole, AdminUser
from app.models.user import User
from app.utils.jwt import create_access_token


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def test_get_current_admin_returns_admin_for_valid_token(db_session):
    admin = AdminUser(email=f"a-{uuid.uuid4()}@example.com", hashed_password="x", role=AdminRole.admin)
    db_session.add(admin)
    await db_session.flush()
    token = create_access_token(subject=str(admin.id))

    result = await get_current_admin(credentials=_bearer(token), db=db_session)

    assert result.id == admin.id


async def test_get_current_admin_rejects_disabled_admin(db_session):
    admin = AdminUser(email=f"a-{uuid.uuid4()}@example.com", hashed_password="x", enabled=False)
    db_session.add(admin)
    await db_session.flush()
    token = create_access_token(subject=str(admin.id))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(credentials=_bearer(token), db=db_session)
    assert exc_info.value.status_code == 401


async def test_get_current_user_returns_user_for_valid_token(db_session):
    user = User(email=f"u-{uuid.uuid4()}@example.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()
    token = create_access_token(subject=str(user.id))

    result = await get_current_user(credentials=_bearer(token), db=db_session)

    assert result.id == user.id


async def test_get_current_user_rejects_invalid_token(db_session):
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=_bearer("not-a-valid-token"), db=db_session)
    assert exc_info.value.status_code == 401
