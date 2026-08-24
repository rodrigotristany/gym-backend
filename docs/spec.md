# Backend Spec

## Environment Variables

| Key | Description | Example |
|---|---|---|
| `ENV` | Environment name: `local`, `dev`, or `prod`. Controls SQL echo logging. | `local` |
| `DATABASE_URL` | Async Postgres connection string (`postgresql+asyncpg://` scheme). | `postgresql+asyncpg://gym:gym@localhost:5434/gym_backend` |
| `SECRET_KEY` | HMAC signing key for JWTs. Must be random and secret in `dev`/`prod`. | `change-me-to-a-random-secret` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime in minutes. | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime in days. | `7` |
| `OTP_EXPIRE_MINUTES` | OTP code lifetime in minutes. | `10` |

## Auth Flows

### Admin login
`POST /admin/auth/login` — `{ email, password }` → `200 { access_token, refresh_token, token_type }` / `401` invalid credentials / `403` account disabled.

### Admin logout
`POST /admin/auth/logout` — Header `Authorization: Bearer <access_token>`, body `{ refresh_token }` → `200 { message }`. Revokes the refresh token server-side. The lookup is scoped to the authenticated caller, so a token belonging to another account (or account type) is silently ignored rather than revoked.

### Admin password recovery
Two-step: `POST /admin/auth/password-recovery/request` — `{ email }` → always `200` (doesn't leak whether the email exists), sends an OTP via `app.utils.email.send_otp_email` (logs the code in this scaffold). `POST /admin/auth/password-recovery/confirm` — `{ email, otp_code, new_password }` → `200 { message }` / `400` invalid or expired OTP. No password-strength rule for admins.

### User registration
`POST /auth/register` — `{ email, password }` → `201 { access_token, refresh_token, token_type }` / `400` weak password / `409` email already registered. Password-strength rules enforced.

### User login / logout
Same shapes as the admin flows, under `/auth/*` instead of `/admin/auth/*`.

### User password recovery
Same two-step shape as admin, under `/auth/password-recovery/*`. Password-strength rules enforced on `new_password`. Confirming a recovery also revokes every outstanding refresh token for that account.

### Token refresh (shared)
`POST /auth/token/refresh` — `{ refresh_token }` → `200 { access_token, refresh_token, token_type }` (rotates the refresh token) / `401` revoked or expired. Works for both admin and user refresh tokens — `RefreshToken.user_type` disambiguates internally.

## Endpoints

| Method | Path | Auth required | Description |
|---|---|---|---|
| GET | `/health` | No | Liveness check |
| POST | `/admin/auth/login` | No | Admin/professor login |
| POST | `/admin/auth/logout` | Bearer (admin) | Revoke a refresh token |
| POST | `/admin/auth/password-recovery/request` | No | Request a password-recovery OTP |
| POST | `/admin/auth/password-recovery/confirm` | No | Confirm OTP + set new password |
| POST | `/auth/register` | No | Register a new end-user account |
| POST | `/auth/login` | No | User login |
| POST | `/auth/logout` | Bearer (user) | Revoke a refresh token |
| POST | `/auth/password-recovery/request` | No | Request a password-recovery OTP |
| POST | `/auth/password-recovery/confirm` | No | Confirm OTP + set new password |
| POST | `/auth/token/refresh` | No (refresh token in body) | Rotate access/refresh tokens |

## Run Commands

Local (no Docker):
```bash
cp .env.example .env
docker compose up -d postgres
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Full stack (Docker):
```bash
cp .env.example .env
docker compose up --build
```

Tests:
```bash
docker compose up -d postgres
alembic upgrade head
pytest
```

## JWT Details

- **Access token**: JWT, HS256, `ACCESS_TOKEN_EXPIRE_MINUTES` lifetime. Claims: `sub` (principal UUID as string), `exp`, `type: "access"`. Bearer authentication rejects any token whose `type` is not `"access"`, so a refresh token cannot be replayed as an access token.
- **Refresh token**: JWT, HS256, `REFRESH_TOKEN_EXPIRE_DAYS` lifetime. Claims: `sub`, `exp`, `type: "refresh"`, `jti` (random per-token id, so two tokens minted in the same second are never identical). Also stored server-side (SHA-256 hash) in `refresh_tokens` so it can be revoked or rotated independent of the JWT's own expiry.
- **Where to send them**: access token in `Authorization: Bearer <access_token>` header on protected endpoints (`/admin/auth/logout`, `/auth/logout`). Refresh token goes in the request body for `/auth/token/refresh` and the `logout` endpoints.
