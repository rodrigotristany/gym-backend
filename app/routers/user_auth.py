from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    PasswordRecoveryConfirm,
    PasswordRecoveryRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["user-auth"])

USER_TYPE = "user"


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.register(db, body.email, body.password)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await auth_service.issue_tokens(db, USER_TYPE, user.id)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await auth_service.authenticate(db, USER_TYPE, body.email, body.password)
        return await auth_service.issue_tokens(db, USER_TYPE, user.id)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await auth_service.revoke_refresh_token(db, USER_TYPE, current_user.id, body.refresh_token)
    return MessageResponse(message="logged out")


@router.post("/password-recovery/request", response_model=MessageResponse)
async def password_recovery_request(body: PasswordRecoveryRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.request_password_recovery(db, USER_TYPE, body.email)
    return MessageResponse(message="if the account exists, an email has been sent")


@router.post("/password-recovery/confirm", response_model=MessageResponse)
async def password_recovery_confirm(body: PasswordRecoveryConfirm, db: AsyncSession = Depends(get_db)):
    try:
        await auth_service.confirm_password_recovery(
            db, USER_TYPE, body.email, body.otp_code, body.new_password, enforce_strength=True
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageResponse(message="password updated")


@router.post("/token/refresh", response_model=TokenResponse)
async def token_refresh(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await auth_service.refresh_access_token(db, body.refresh_token)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
