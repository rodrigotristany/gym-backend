from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_admin, get_db
from app.models.admin_user import AdminUser
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    PasswordRecoveryConfirm,
    PasswordRecoveryRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])

USER_TYPE = "admin"


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        admin = await auth_service.authenticate(db, USER_TYPE, body.email, body.password)
        return await auth_service.issue_tokens(db, USER_TYPE, admin.id)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
):
    await auth_service.revoke_refresh_token(db, USER_TYPE, current_admin.id, body.refresh_token)
    return MessageResponse(message="logged out")


@router.post("/password-recovery/request", response_model=MessageResponse)
async def password_recovery_request(body: PasswordRecoveryRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.request_password_recovery(db, USER_TYPE, body.email)
    return MessageResponse(message="if the account exists, an email has been sent")


@router.post("/password-recovery/confirm", response_model=MessageResponse)
async def password_recovery_confirm(body: PasswordRecoveryConfirm, db: AsyncSession = Depends(get_db)):
    try:
        await auth_service.confirm_password_recovery(
            db, USER_TYPE, body.email, body.otp_code, body.new_password, enforce_strength=False
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageResponse(message="password updated")
