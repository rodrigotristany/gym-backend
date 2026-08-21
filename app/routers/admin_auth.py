from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_admin, get_db
from app.models.admin_user import AdminUser
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    OtpVerifyRequest,
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
    _: AdminUser = Depends(get_current_admin),
):
    await auth_service.revoke_refresh_token(db, body.refresh_token)
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
    return MessageResponse(message="password updated")


@router.post("/otp/verify", response_model=TokenResponse)
async def otp_verify(body: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    admin = await auth_service.get_principal_by_email(db, USER_TYPE, body.email)
    if admin is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    try:
        await auth_service.verify_otp(db, USER_TYPE, admin.id, "login_otp", body.otp_code)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await auth_service.issue_tokens(db, USER_TYPE, admin.id)
