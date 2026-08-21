import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.admin_user import AdminUser
from app.models.otp import OtpCode
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.utils.email import send_otp_email
from app.utils.hashing import sha256_hex
from app.utils.jwt import create_access_token, create_refresh_token, decode_token
from app.utils.otp import generate_otp_code, hash_otp_code
from app.utils.password import hash_password, validate_password_strength, verify_password

UserType = Literal["admin", "user"]

MODELS_BY_TYPE: dict[UserType, type] = {"admin": AdminUser, "user": User}


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def authenticate(db: AsyncSession, user_type: UserType, email: str, password: str):
    model = MODELS_BY_TYPE[user_type]
    result = await db.execute(select(model).where(model.email == email))
    principal = result.scalar_one_or_none()
    if principal is None or not verify_password(password, principal.hashed_password):
        raise AuthError(401, "Invalid credentials")
    if not principal.enabled:
        raise AuthError(403, "Account disabled")
    return principal


async def issue_tokens(db: AsyncSession, user_type: UserType, principal_id: uuid.UUID) -> dict:
    subject = str(principal_id)
    access_token = create_access_token(subject=subject)
    refresh_token = create_refresh_token(subject=subject)

    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(
        RefreshToken(
            token_hash=sha256_hex(refresh_token),
            user_id=principal_id,
            user_type=user_type,
            expires_at=expires_at,
        )
    )
    await db.flush()

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except Exception as exc:
        raise AuthError(401, "Invalid or expired refresh token") from exc
    if payload.get("type") != "refresh":
        raise AuthError(401, "Invalid or expired refresh token")

    token_hash = sha256_hex(refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored is None or stored.revoked or stored.expires_at < datetime.now(timezone.utc):
        raise AuthError(401, "Invalid or expired refresh token")

    stored.revoked = True
    await db.flush()

    return await issue_tokens(db, stored.user_type, stored.user_id)


async def revoke_refresh_token(db: AsyncSession, refresh_token: str) -> None:
    token_hash = sha256_hex(refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored is not None:
        stored.revoked = True
        await db.flush()


async def create_otp(db: AsyncSession, user_type: UserType, principal_id: uuid.UUID, purpose: str) -> str:
    code = generate_otp_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    db.add(
        OtpCode(
            code_hash=hash_otp_code(code),
            user_id=principal_id,
            user_type=user_type,
            purpose=purpose,
            expires_at=expires_at,
        )
    )
    await db.flush()
    return code


async def verify_otp(
    db: AsyncSession, user_type: UserType, principal_id: uuid.UUID, purpose: str, code: str
) -> None:
    result = await db.execute(
        select(OtpCode).where(
            OtpCode.user_id == principal_id,
            OtpCode.user_type == user_type,
            OtpCode.purpose == purpose,
            OtpCode.code_hash == hash_otp_code(code),
            OtpCode.used.is_(False),
        )
    )
    otp = result.scalar_one_or_none()
    if otp is None or otp.expires_at < datetime.now(timezone.utc):
        raise AuthError(400, "Invalid or expired OTP")
    otp.used = True
    await db.flush()


async def register(db: AsyncSession, email: str, password: str) -> User:
    validate_password_strength(password)

    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none() is not None:
        raise AuthError(409, "Email already registered")

    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    await db.flush()
    return user


async def get_principal_by_email(db: AsyncSession, user_type: UserType, email: str):
    model = MODELS_BY_TYPE[user_type]
    result = await db.execute(select(model).where(model.email == email))
    return result.scalar_one_or_none()


async def request_password_recovery(db: AsyncSession, user_type: UserType, email: str) -> None:
    model = MODELS_BY_TYPE[user_type]
    result = await db.execute(select(model).where(model.email == email))
    principal = result.scalar_one_or_none()
    if principal is None:
        return
    code = await create_otp(db, user_type, principal.id, "password_recovery")
    send_otp_email(email, code, "password_recovery")


async def confirm_password_recovery(
    db: AsyncSession,
    user_type: UserType,
    email: str,
    otp_code: str,
    new_password: str,
    enforce_strength: bool,
) -> None:
    if enforce_strength:
        validate_password_strength(new_password)

    model = MODELS_BY_TYPE[user_type]
    result = await db.execute(select(model).where(model.email == email))
    principal = result.scalar_one_or_none()
    if principal is None:
        raise AuthError(400, "Invalid or expired OTP")

    await verify_otp(db, user_type, principal.id, "password_recovery", otp_code)

    principal.hashed_password = hash_password(new_password)
    await db.flush()
