from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class MessageResponse(BaseModel):
    message: str


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class PasswordRecoveryConfirm(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str


class OtpVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
