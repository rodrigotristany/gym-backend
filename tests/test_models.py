import uuid

from sqlalchemy import select

from app.models.admin_user import AdminRole, AdminUser
from app.models.user import User


async def test_create_and_fetch_admin_user(db_session):
    admin = AdminUser(
        email=f"admin-{uuid.uuid4()}@example.com",
        hashed_password="hashed",
        role=AdminRole.admin,
    )
    db_session.add(admin)
    await db_session.flush()

    result = await db_session.execute(select(AdminUser).where(AdminUser.id == admin.id))
    fetched = result.scalar_one()
    assert fetched.email == admin.email
    assert fetched.role == AdminRole.admin
    assert fetched.enabled is True


async def test_create_and_fetch_user(db_session):
    user = User(email=f"user-{uuid.uuid4()}@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()

    result = await db_session.execute(select(User).where(User.id == user.id))
    fetched = result.scalar_one()
    assert fetched.email == user.email
    assert fetched.enabled is True
