# Backend Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the initial FastAPI backend skeleton for the gym platform — project structure, database connectivity, and a full first-party auth system for `admin_users` and `users` — with no exercise/routine domain models yet.

**Architecture:** FastAPI app with a service layer (`app/services/auth_service.py`) shared by two parallel routers (`admin_auth`, `user_auth`) that differ only in which model/user_type they operate on and whether password-strength rules apply. Async SQLAlchemy 2.0 talks to PostgreSQL via `asyncpg`; Alembic owns schema migrations. Local dev and tests run against a single Docker Compose Postgres instance; each test wraps its work in a transaction that's rolled back afterward for isolation.

**Tech Stack:** Python >= 3.12, FastAPI, SQLAlchemy 2.0 (async), asyncpg, Alembic, PostgreSQL 16, PyJWT, bcrypt, pytest + pytest-asyncio + httpx, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-21-backend-scaffold-design.md`

## Global Constraints

- Python >= 3.12.
- `DATABASE_URL` uses the `postgresql+asyncpg://` scheme for the app; Alembic converts to `postgresql+psycopg2://` for its own sync runner.
- Three environments via `ENV` setting: `local`, `dev`, `prod`. SQL echo logging only when `ENV == "local"`.
- `ACCESS_TOKEN_EXPIRE_MINUTES` default 30, `REFRESH_TOKEN_EXPIRE_DAYS` default 7, `OTP_EXPIRE_MINUTES` default 10.
- Refresh tokens are stored server-side (hashed with SHA-256) in a `refresh_tokens` table — never trust a bare JWT for refresh; always check the DB row (exists, not revoked, not expired).
- OTP codes are 6 digits, single-use, stored hashed (SHA-256), scoped by `purpose` (`"login_otp"` | `"password_recovery"`).
- Passwords hashed with bcrypt; **never** logged or returned in any response.
- User (not admin) passwords must pass strength validation (>=8 chars, upper, lower, digit, symbol) on registration and password recovery. Admin passwords have no strength restriction.
- No third-party OAuth — first-party auth only.
- DB calls live in `app/services/`, never directly in routers. Routers depend on `Depends(get_db)` and services for all persistence.
- Pydantic schemas are separate from ORM models — build responses with plain dicts or `model_validate`, never `.from_orm()`.
- `HTTPException` with a clear `detail` string is the only error-handling mechanism in this pass — no global exception framework.
- Every DB table uses the shared SQLAlchemy naming convention (see Task 3) for predictable constraint names across migrations.

---

## File Structure

```
app/
├── __init__.py
├── main.py                    # FastAPI app factory, includes all routers
├── config.py                  # Pydantic Settings
├── database.py                # Base (w/ naming convention), async engine, session factory
├── dependencies.py            # get_db, get_current_admin, get_current_user
├── models/
│   ├── __init__.py             # imports all models so Alembic autogenerate sees them
│   ├── mixins.py                # TimestampMixin
│   ├── admin_user.py             # AdminUser, AdminRole
│   ├── user.py                    # User
│   ├── refresh_token.py            # RefreshToken
│   └── otp.py                       # OtpCode
├── schemas/
│   ├── __init__.py
│   └── auth.py                 # Shared request/response schemas for both auth routers
├── routers/
│   ├── __init__.py
│   ├── health.py
│   ├── admin_auth.py
│   └── user_auth.py
├── services/
│   ├── __init__.py
│   └── auth_service.py         # All auth business logic, parameterized by user_type
└── utils/
    ├── __init__.py
    ├── hashing.py               # sha256_hex — shared by OTP + refresh token hashing
    ├── password.py               # hash/verify/validate_strength
    ├── jwt.py                     # create_access_token, create_refresh_token, decode_token
    ├── otp.py                      # generate/hash/verify OTP codes
    └── email.py                     # send_otp_email (console/log backend)
alembic/
├── env.py
├── script.py.mako
└── versions/                  # generated migration(s)
alembic.ini
requirements.txt
pytest.ini
.env.example
.env                          # local only, gitignored, created via `cp .env.example .env`
Dockerfile
docker-compose.yml
docs/
└── spec.md                    # generated last (Task 11)
tests/
├── conftest.py
├── test_health.py
├── test_config.py
├── test_database.py
├── test_models.py
├── test_utils_password.py
├── test_utils_jwt.py
├── test_utils_otp.py
├── test_utils_email.py
├── test_dependencies.py
├── test_auth_service.py
├── test_admin_auth_router.py
└── test_user_auth_router.py
```

---

### Task 1: Project skeleton & health endpoint

**Files:**
- Create: `requirements.txt`, `pytest.ini`
- Create: `app/__init__.py`, `app/main.py`
- Create: `app/routers/__init__.py`, `app/routers/health.py`
- Test: `tests/conftest.py`, `tests/test_health.py`

**Interfaces:**
- Produces: `app.main.app` (the FastAPI instance later tasks mount routers onto), `tests/conftest.py::client` fixture (async httpx client against the app, replaced with a DB-aware version in Task 8).

- [ ] **Step 1: Create project structure and dependency files**

`requirements.txt`:
```
fastapi>=0.115,<1.0
uvicorn[standard]>=0.30
sqlalchemy[asyncio]>=2.0,<3.0
asyncpg>=0.29
alembic>=1.13
pydantic-settings>=2.0
pydantic[email]>=2.0
pyjwt>=2.8
bcrypt>=4.0
python-multipart>=0.0.9
python-slugify>=8.0

# Dev / testing
pytest>=8.0
pytest-asyncio>=0.23
httpx>=0.27
psycopg2-binary>=2.9
```

`pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

Run: `python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

- [ ] **Step 2: Write the failing test**

`tests/conftest.py`:
```python
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

`tests/test_health.py`:
```python
async def test_health_check_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_health.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'` (or `'app.main'`).

- [ ] **Step 4: Implement the minimal app**

`app/__init__.py`: empty file.

`app/routers/__init__.py`: empty file.

`app/routers/health.py`:
```python
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
```

`app/main.py`:
```python
from fastapi import FastAPI

from app.routers import health


def create_app() -> FastAPI:
    app = FastAPI(title="Gym Backend")
    app.include_router(health.router)
    return app


app = create_app()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini app/ tests/conftest.py tests/test_health.py
git commit -m "feat: scaffold FastAPI app with health check endpoint"
```

---

### Task 2: Local Postgres (Docker Compose) & Settings

**Files:**
- Create: `docker-compose.yml`, `.env.example`
- Create: `app/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing from prior tasks.
- Produces: `app.config.settings` (a `Settings` instance) — `settings.DATABASE_URL`, `settings.SECRET_KEY`, `settings.ENV`, `settings.ACCESS_TOKEN_EXPIRE_MINUTES`, `settings.REFRESH_TOKEN_EXPIRE_DAYS`, `settings.OTP_EXPIRE_MINUTES` are used by every later task that touches the DB, JWTs, or OTPs.

- [ ] **Step 1: Write Docker Compose for local Postgres and the env template**

`docker-compose.yml`:
```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: gym
      POSTGRES_PASSWORD: gym
      POSTGRES_DB: gym_backend
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gym -d gym_backend"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

`.env.example`:
```
ENV=local
DATABASE_URL=postgresql+asyncpg://gym:gym@localhost:5432/gym_backend
SECRET_KEY=change-me-to-a-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
OTP_EXPIRE_MINUTES=10
```

Run:
```bash
cp .env.example .env
docker compose up -d postgres
docker compose exec postgres pg_isready -U gym -d gym_backend
```
Expected: `... accepting connections`

- [ ] **Step 2: Write the failing test**

`tests/test_config.py`:
```python
from app.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@host:5432/db")
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    settings = Settings(_env_file=None)

    assert settings.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"
    assert settings.SECRET_KEY == "test-secret"
    assert settings.ENV == "local"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
    assert settings.OTP_EXPIRE_MINUTES == 10
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 4: Implement settings**

`app/config.py`:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENV: str = "local"
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    OTP_EXPIRE_MINUTES: int = 10


settings = Settings()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml .env.example app/config.py tests/test_config.py
git commit -m "feat: add local Postgres via Docker Compose and app settings"
```

Note: `.env` is intentionally not committed (already covered by `.gitignore`'s `.env` rule) — every later task assumes it exists locally with the values above.

---

### Task 3: Database engine, session, Base, TimestampMixin

**Files:**
- Create: `app/database.py`, `app/models/__init__.py`, `app/models/mixins.py`, `app/dependencies.py`
- Test: `tests/test_database.py`

**Interfaces:**
- Consumes: `app.config.settings` (Task 2).
- Produces: `app.database.Base` (declarative base with naming convention — all models inherit from it), `app.database.engine`, `app.database.AsyncSessionLocal`, `app.models.mixins.TimestampMixin`, `app.dependencies.get_db` (FastAPI dependency yielding an `AsyncSession`, committing on success / rolling back on exception).

- [ ] **Step 1: Write the failing test**

`tests/test_database.py`:
```python
from sqlalchemy import text

from app.database import engine


async def test_engine_connects_to_database():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.database'`

- [ ] **Step 3: Implement database layer**

`app/database.py`:
```python
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENV == "local",
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)
```

`app/models/__init__.py`: empty for now (populated in Task 4).

`app/models/mixins.py`:
```python
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

`app/dependencies.py`:
```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py -v`
Expected: PASS (requires `docker compose up -d postgres` from Task 2 to still be running)

- [ ] **Step 5: Commit**

```bash
git add app/database.py app/models/__init__.py app/models/mixins.py app/dependencies.py tests/test_database.py
git commit -m "feat: add async SQLAlchemy engine, session factory, and TimestampMixin"
```

---

### Task 4: Auth data models & initial Alembic migration

**Files:**
- Create: `app/models/admin_user.py`, `app/models/user.py`, `app/models/refresh_token.py`, `app/models/otp.py`
- Modify: `app/models/__init__.py`
- Create: `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/<generated>.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: `app.database.Base`, `app.models.mixins.TimestampMixin` (Task 3).
- Produces: `app.models.admin_user.AdminUser`, `app.models.admin_user.AdminRole` (enum: `admin`, `professor`), `app.models.user.User`, `app.models.refresh_token.RefreshToken`, `app.models.otp.OtpCode`. `tests/conftest.py::db_session` fixture (a transactional `AsyncSession`, rolled back after each test) — used by every remaining test file that touches the DB.

- [ ] **Step 1: Create model files and Alembic scaffolding**

`app/models/admin_user.py`:
```python
import enum
import uuid

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TimestampMixin


class AdminRole(str, enum.Enum):
    admin = "admin"
    professor = "professor"


class AdminUser(Base, TimestampMixin):
    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[AdminRole] = mapped_column(
        PgEnum(AdminRole, name="admin_role"), default=AdminRole.professor, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

`app/models/user.py`:
```python
import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

`app/models/refresh_token.py`:
```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_type: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

`app/models/otp.py`:
```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    user_type: Mapped[str] = mapped_column(String(20), nullable=False)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

`app/models/__init__.py`:
```python
from app.models.admin_user import AdminRole, AdminUser
from app.models.otp import OtpCode
from app.models.refresh_token import RefreshToken
from app.models.user import User

__all__ = ["AdminUser", "AdminRole", "User", "RefreshToken", "OtpCode"]
```

Run: `alembic init alembic`

Replace `alembic/env.py` with:
```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  (registers all models on Base.metadata)
from app.config import settings
from app.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sync_url() -> str:
    return settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")


def run_migrations_offline() -> None:
    context.configure(
        url=get_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_sync_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

In `alembic.ini`, delete/comment out the generated `sqlalchemy.url = driver://...` line — the URL is set programmatically in `env.py`.

- [ ] **Step 2: Write the failing test and DB session fixture**

Add to `tests/conftest.py` (keep the existing `client` fixture from Task 1):
```python
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database import engine
from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()
```

`tests/test_models.py`:
```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with a database error like `relation "admin_users" does not exist` (tables don't exist yet — no migration has been generated or applied).

- [ ] **Step 4: Generate and apply the migration**

```bash
alembic revision --autogenerate -m "create auth tables"
```
Open the generated file in `alembic/versions/` and confirm it contains `op.create_table(...)` for all four tables: `admin_users`, `users`, `refresh_tokens`, `otp_codes`. If any table is missing, check that `app/models/__init__.py` imports it and regenerate.

```bash
alembic upgrade head
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/models/ alembic.ini alembic/ tests/conftest.py tests/test_models.py
git commit -m "feat: add admin_users, users, refresh_tokens, otp_codes models and initial migration"
```

---

### Task 5: Password / JWT / OTP / Email utilities

**Files:**
- Create: `app/utils/__init__.py`, `app/utils/hashing.py`, `app/utils/password.py`, `app/utils/jwt.py`, `app/utils/otp.py`, `app/utils/email.py`
- Test: `tests/test_utils_password.py`, `tests/test_utils_jwt.py`, `tests/test_utils_otp.py`, `tests/test_utils_email.py`

**Interfaces:**
- Consumes: `app.config.settings` (Task 2).
- Produces: `hash_password`, `verify_password`, `validate_password_strength` (`app.utils.password`); `create_access_token`, `create_refresh_token`, `decode_token` (`app.utils.jwt`); `generate_otp_code`, `hash_otp_code`, `verify_otp_code` (`app.utils.otp`); `sha256_hex` (`app.utils.hashing`); `send_otp_email` (`app.utils.email`). All consumed by `app/services/auth_service.py` (Task 7) and `app/dependencies.py` (Task 6).

- [ ] **Step 1: Write the failing tests**

`app/utils/__init__.py`: empty file.

`tests/test_utils_password.py`:
```python
import pytest

from app.utils.password import hash_password, validate_password_strength, verify_password


def test_hash_and_verify_password_roundtrip():
    hashed = hash_password("Str0ng!Pass")
    assert hashed != "Str0ng!Pass"
    assert verify_password("Str0ng!Pass", hashed) is True
    assert verify_password("wrong", hashed) is False


@pytest.mark.parametrize(
    "password",
    ["Str0ng!", "nouppercase1!", "NOLOWERCASE1!", "NoDigitsHere!", "NoSymbols1here"],
)
def test_validate_password_strength_rejects_weak_passwords(password):
    with pytest.raises(ValueError):
        validate_password_strength(password)


def test_validate_password_strength_accepts_strong_password():
    validate_password_strength("Str0ng!Pass")
```

`tests/test_utils_jwt.py`:
```python
from app.utils.jwt import create_access_token, create_refresh_token, decode_token


def test_create_and_decode_access_token():
    token = create_access_token(subject="user-id-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-id-123"


def test_create_and_decode_refresh_token():
    token = create_refresh_token(subject="user-id-123")
    payload = decode_token(token)
    assert payload["sub"] == "user-id-123"
    assert payload["type"] == "refresh"
```

`tests/test_utils_otp.py`:
```python
from app.utils.otp import generate_otp_code, hash_otp_code, verify_otp_code


def test_generate_otp_code_is_six_digits():
    code = generate_otp_code()
    assert len(code) == 6
    assert code.isdigit()


def test_hash_and_verify_otp_code_roundtrip():
    code = generate_otp_code()
    code_hash = hash_otp_code(code)
    assert verify_otp_code(code, code_hash) is True
    assert verify_otp_code("000000", code_hash) is False
```

`tests/test_utils_email.py`:
```python
import logging

from app.utils.email import send_otp_email


def test_send_otp_email_logs_the_code(caplog):
    with caplog.at_level(logging.INFO, logger="app.email"):
        send_otp_email("user@example.com", "123456", "login_otp")
    assert "123456" in caplog.text
    assert "user@example.com" in caplog.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_utils_password.py tests/test_utils_jwt.py tests/test_utils_otp.py tests/test_utils_email.py -v`
Expected: FAIL with `ModuleNotFoundError` for each `app.utils.*` module.

- [ ] **Step 3: Implement the utilities**

`app/utils/hashing.py`:
```python
import hashlib


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
```

`app/utils/password.py`:
```python
import re

import bcrypt

PASSWORD_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]).{8,}$'
)


def validate_password_strength(password: str) -> None:
    if not PASSWORD_PATTERN.match(password):
        raise ValueError(
            "Password must be at least 8 characters and include uppercase, "
            "lowercase, a number, and a symbol."
        )


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
```

`app/utils/jwt.py`:
```python
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

ALGORITHM = "HS256"


def create_access_token(subject: str, extra: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire, **(extra or {})}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "type": "refresh", "jti": secrets.token_hex(16)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
```

`app/utils/otp.py`:
```python
import secrets

from app.utils.hashing import sha256_hex


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp_code(code: str) -> str:
    return sha256_hex(code)


def verify_otp_code(code: str, code_hash: str) -> bool:
    return sha256_hex(code) == code_hash
```

`app/utils/email.py`:
```python
import logging

logger = logging.getLogger("app.email")


def send_otp_email(to_email: str, code: str, purpose: str) -> None:
    logger.info("OTP email to=%s purpose=%s code=%s", to_email, purpose, code)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_utils_password.py tests/test_utils_jwt.py tests/test_utils_otp.py tests/test_utils_email.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/utils/ tests/test_utils_password.py tests/test_utils_jwt.py tests/test_utils_otp.py tests/test_utils_email.py
git commit -m "feat: add password, JWT, OTP, and email utilities"
```

---

### Task 6: Auth dependencies (get_current_admin, get_current_user)

**Files:**
- Modify: `app/dependencies.py`
- Test: `tests/test_dependencies.py`

**Interfaces:**
- Consumes: `app.models.admin_user.AdminUser`, `app.models.user.User` (Task 4), `app.utils.jwt.decode_token` (Task 5).
- Produces: `get_current_admin(credentials, db) -> AdminUser`, `get_current_user(credentials, db) -> User` — both raise `HTTPException(401)` for missing/invalid/expired tokens or disabled accounts. Used by `admin_auth.py`/`user_auth.py` routers (Tasks 8-9) to protect `logout`.

- [ ] **Step 1: Write the failing test**

`tests/test_dependencies.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dependencies.py -v`
Expected: FAIL with `ImportError: cannot import name 'get_current_admin' from 'app.dependencies'`

- [ ] **Step 3: Implement the dependencies**

`app/dependencies.py`:
```python
import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.admin_user import AdminUser
from app.models.user import User
from app.utils.jwt import decode_token

bearer_scheme = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def _subject_to_uuid(payload: dict) -> uuid.UUID:
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    try:
        payload = decode_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    admin = await db.get(AdminUser, _subject_to_uuid(payload))
    if admin is None or not admin.enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return admin


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    user = await db.get(User, _subject_to_uuid(payload))
    if user is None or not user.enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return user
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dependencies.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/dependencies.py tests/test_dependencies.py
git commit -m "feat: add get_current_admin and get_current_user auth dependencies"
```

---

### Task 7: Generic auth service layer

**Files:**
- Create: `app/services/__init__.py`, `app/services/auth_service.py`
- Test: `tests/test_auth_service.py`

**Interfaces:**
- Consumes: `AdminUser`, `User`, `RefreshToken`, `OtpCode` (Task 4); `hash_password`, `verify_password`, `validate_password_strength`, `create_access_token`, `create_refresh_token`, `decode_token`, `generate_otp_code`, `hash_otp_code`, `sha256_hex`, `send_otp_email` (Task 5).
- Produces: `AuthError(status_code, detail)` exception; `authenticate`, `issue_tokens`, `refresh_access_token`, `revoke_refresh_token`, `create_otp`, `verify_otp`, `register`, `request_password_recovery`, `confirm_password_recovery`, `get_principal_by_email` — all `async`, taking `db: AsyncSession` first. Consumed by `admin_auth.py`/`user_auth.py` routers (Tasks 8-9), which convert `AuthError`/`ValueError` into `HTTPException`. `get_principal_by_email` exists so routers never issue a raw `select()` themselves (Global Constraints: DB calls live in services, not routers) — the `otp/verify` endpoints need to resolve an email to a principal before calling `verify_otp`, which takes an id.

- [ ] **Step 1: Write the failing tests**

`app/services/__init__.py`: empty file.

`tests/test_auth_service.py`:
```python
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

    await auth_service.revoke_refresh_token(db_session, tokens["refresh_token"])

    with pytest.raises(auth_service.AuthError):
        await auth_service.refresh_access_token(db_session, tokens["refresh_token"])


async def test_create_and_verify_otp_roundtrip(db_session):
    user = await _make_user(db_session)
    code = await auth_service.create_otp(db_session, "user", user.id, "login_otp")
    await auth_service.verify_otp(db_session, "user", user.id, "login_otp", code)


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_auth_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services'`

- [ ] **Step 3: Implement the service layer**

`app/services/auth_service.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_auth_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/ tests/test_auth_service.py
git commit -m "feat: add generic auth service layer (authenticate, tokens, OTP, password recovery)"
```

---

### Task 8: Admin auth router & schemas

**Files:**
- Create: `app/schemas/__init__.py`, `app/schemas/auth.py`
- Create: `app/routers/admin_auth.py`
- Modify: `app/main.py`, `tests/conftest.py`
- Test: `tests/test_admin_auth_router.py`

**Interfaces:**
- Consumes: `app.services.auth_service.*` (Task 7), `app.dependencies.get_db`, `get_current_admin` (Task 6), `app.models.admin_user.AdminUser` (Task 4).
- Produces: `POST /admin/auth/login`, `/logout`, `/password-recovery/request`, `/password-recovery/confirm`, `/otp/verify`. Shared schemas in `app.schemas.auth` (`LoginRequest`, `TokenResponse`, `RefreshTokenRequest`, `MessageResponse`, `PasswordRecoveryRequest`, `PasswordRecoveryConfirm`, `OtpVerifyRequest`) reused by `user_auth.py` (Task 9). `tests/conftest.py::client` now DB-backed (shares `db_session`'s transaction) — this replaces the plain fixture from Task 1 and is the version every later router test uses.

- [ ] **Step 1: Write the failing tests**

`app/schemas/__init__.py`: empty file.

`app/schemas/auth.py`:
```python
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
```

Update `tests/conftest.py` — replace the `client` fixture (keep `db_session` as-is):
```python
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database import engine
from app.dependencies import get_db
from app.main import app


@pytest_asyncio.fixture
async def db_session():
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

`tests/test_admin_auth_router.py`:
```python
import logging
import re
import uuid

from app.models.admin_user import AdminRole, AdminUser
from app.services import auth_service
from app.utils.password import hash_password


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


async def test_login_returns_tokens_for_valid_credentials(client, db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass")

    response = await client.post("/admin/auth/login", json={"email": admin.email, "password": "Str0ng!Pass"})

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_login_rejects_wrong_password(client, db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass")

    response = await client.post("/admin/auth/login", json={"email": admin.email, "password": "wrong"})

    assert response.status_code == 401


async def test_login_rejects_disabled_account(client, db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass", enabled=False)

    response = await client.post("/admin/auth/login", json={"email": admin.email, "password": "Str0ng!Pass"})

    assert response.status_code == 403


async def test_logout_revokes_refresh_token(client, db_session):
    admin = await _make_admin(db_session, password="Str0ng!Pass")
    login_response = await client.post(
        "/admin/auth/login", json={"email": admin.email, "password": "Str0ng!Pass"}
    )
    tokens = login_response.json()

    response = await client.post(
        "/admin/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200


async def test_logout_requires_authentication(client):
    response = await client.post("/admin/auth/logout", json={"refresh_token": "x"})
    assert response.status_code == 403


async def test_password_recovery_flow(client, db_session, caplog):
    admin = await _make_admin(db_session, password="Str0ng!Pass")

    with caplog.at_level(logging.INFO, logger="app.email"):
        request_response = await client.post(
            "/admin/auth/password-recovery/request", json={"email": admin.email}
        )
    assert request_response.status_code == 200
    code = re.search(r"code=(\d{6})", caplog.text).group(1)

    confirm_response = await client.post(
        "/admin/auth/password-recovery/confirm",
        json={"email": admin.email, "otp_code": code, "new_password": "weak"},
    )

    assert confirm_response.status_code == 200


async def test_password_recovery_request_is_silent_for_unknown_email(client):
    response = await client.post(
        "/admin/auth/password-recovery/request", json={"email": "nobody@example.com"}
    )
    assert response.status_code == 200


async def test_otp_verify_returns_tokens(client, db_session):
    admin = await _make_admin(db_session)
    code = await auth_service.create_otp(db_session, "admin", admin.id, "login_otp")

    response = await client.post("/admin/auth/otp/verify", json={"email": admin.email, "otp_code": code})

    assert response.status_code == 200
    assert "access_token" in response.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_admin_auth_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.routers.admin_auth'`

- [ ] **Step 3: Implement the router**

`app/routers/admin_auth.py`:
```python
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
```

`app/main.py`:
```python
from fastapi import FastAPI

from app.routers import admin_auth, health


def create_app() -> FastAPI:
    app = FastAPI(title="Gym Backend")
    app.include_router(health.router)
    app.include_router(admin_auth.router)
    return app


app = create_app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_admin_auth_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/schemas/ app/routers/admin_auth.py app/main.py tests/conftest.py tests/test_admin_auth_router.py
git commit -m "feat: add admin auth router (login, logout, password recovery, OTP verify)"
```

---

### Task 9: User auth router (register, login, logout, OTP, password recovery, shared token refresh)

**Files:**
- Modify: `app/schemas/auth.py`, `app/main.py`
- Create: `app/routers/user_auth.py`
- Test: `tests/test_user_auth_router.py`

**Interfaces:**
- Consumes: `app.services.auth_service.*` (Task 7, including `register`), `app.dependencies.get_db`, `get_current_user` (Task 6), `app.models.user.User` (Task 4).
- Produces: `POST /auth/register`, `/login`, `/logout`, `/password-recovery/request`, `/password-recovery/confirm`, `/otp/verify`, `/token/refresh` (shared refresh endpoint — works for both admin and user refresh tokens since `RefreshToken.user_type` disambiguates).

- [ ] **Step 1: Write the failing tests**

Add to `app/schemas/auth.py` (append, keep existing classes):
```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
```

`tests/test_user_auth_router.py`:
```python
import logging
import re
import uuid

from app.models.user import User
from app.services import auth_service
from app.utils.password import hash_password


async def _make_user(db_session, password="Str0ng!Pass", enabled=True):
    user = User(
        email=f"user-{uuid.uuid4()}@example.com",
        hashed_password=hash_password(password),
        enabled=enabled,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_register_creates_user_and_returns_tokens(client):
    response = await client.post(
        "/auth/register",
        json={"email": f"new-{uuid.uuid4()}@example.com", "password": "Str0ng!Pass"},
    )

    assert response.status_code == 201
    assert "access_token" in response.json()


async def test_register_rejects_weak_password(client):
    response = await client.post(
        "/auth/register",
        json={"email": f"new-{uuid.uuid4()}@example.com", "password": "weak"},
    )

    assert response.status_code == 400


async def test_register_rejects_duplicate_email(client, db_session):
    user = await _make_user(db_session)

    response = await client.post(
        "/auth/register", json={"email": user.email, "password": "Str0ng!Pass"}
    )

    assert response.status_code == 409


async def test_login_returns_tokens_for_valid_credentials(client, db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")

    response = await client.post("/auth/login", json={"email": user.email, "password": "Str0ng!Pass"})

    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_rejects_disabled_account(client, db_session):
    user = await _make_user(db_session, password="Str0ng!Pass", enabled=False)

    response = await client.post("/auth/login", json={"email": user.email, "password": "Str0ng!Pass"})

    assert response.status_code == 403


async def test_logout_revokes_refresh_token(client, db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")
    login_response = await client.post(
        "/auth/login", json={"email": user.email, "password": "Str0ng!Pass"}
    )
    tokens = login_response.json()

    response = await client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 200


async def test_password_recovery_flow_enforces_strength(client, db_session, caplog):
    user = await _make_user(db_session, password="Str0ng!Pass")

    with caplog.at_level(logging.INFO, logger="app.email"):
        await client.post("/auth/password-recovery/request", json={"email": user.email})
    code = re.search(r"code=(\d{6})", caplog.text).group(1)

    weak_response = await client.post(
        "/auth/password-recovery/confirm",
        json={"email": user.email, "otp_code": code, "new_password": "weak"},
    )
    assert weak_response.status_code == 400

    strong_response = await client.post(
        "/auth/password-recovery/confirm",
        json={"email": user.email, "otp_code": code, "new_password": "N3w!Passw0rd"},
    )
    assert strong_response.status_code == 200


async def test_otp_verify_returns_tokens(client, db_session):
    user = await _make_user(db_session)
    code = await auth_service.create_otp(db_session, "user", user.id, "login_otp")

    response = await client.post("/auth/otp/verify", json={"email": user.email, "otp_code": code})

    assert response.status_code == 200


async def test_token_refresh_rotates_tokens(client, db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")
    login_response = await client.post(
        "/auth/login", json={"email": user.email, "password": "Str0ng!Pass"}
    )
    tokens = login_response.json()

    response = await client.post("/auth/token/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    assert response.json()["refresh_token"] != tokens["refresh_token"]


async def test_token_refresh_rejects_reused_token(client, db_session):
    user = await _make_user(db_session, password="Str0ng!Pass")
    login_response = await client.post(
        "/auth/login", json={"email": user.email, "password": "Str0ng!Pass"}
    )
    tokens = login_response.json()
    await client.post("/auth/token/refresh", json={"refresh_token": tokens["refresh_token"]})

    response = await client.post("/auth/token/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_user_auth_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.routers.user_auth'`

- [ ] **Step 3: Implement the router**

`app/routers/user_auth.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    OtpVerifyRequest,
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
    _: User = Depends(get_current_user),
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
            db, USER_TYPE, body.email, body.otp_code, body.new_password, enforce_strength=True
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MessageResponse(message="password updated")


@router.post("/otp/verify", response_model=TokenResponse)
async def otp_verify(body: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.get_principal_by_email(db, USER_TYPE, body.email)
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    try:
        await auth_service.verify_otp(db, USER_TYPE, user.id, "login_otp", body.otp_code)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await auth_service.issue_tokens(db, USER_TYPE, user.id)


@router.post("/token/refresh", response_model=TokenResponse)
async def token_refresh(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await auth_service.refresh_access_token(db, body.refresh_token)
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
```

`app/main.py`:
```python
from fastapi import FastAPI

from app.routers import admin_auth, health, user_auth


def create_app() -> FastAPI:
    app = FastAPI(title="Gym Backend")
    app.include_router(health.router)
    app.include_router(admin_auth.router)
    app.include_router(user_auth.router)
    return app


app = create_app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_user_auth_router.py -v`
Expected: PASS

Run the full suite to confirm nothing regressed: `pytest -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/schemas/auth.py app/routers/user_auth.py app/main.py tests/test_user_auth_router.py
git commit -m "feat: add user auth router (register, login, logout, password recovery, OTP, token refresh)"
```

---

### Task 10: Containerize the app (Dockerfile + full Docker Compose)

**Files:**
- Create: `Dockerfile`, `.dockerignore`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: `requirements.txt` (Task 1), `app/` (all prior tasks), `alembic/` (Task 4).
- Produces: a runnable `app` service reachable at `http://localhost:8000`, running migrations on startup before serving.

- [ ] **Step 1: Write the Dockerfile and .dockerignore**

`Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`.dockerignore`:
```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.git/
.env
```

- [ ] **Step 2: Add the `app` service to Docker Compose**

`docker-compose.yml`:
```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: gym
      POSTGRES_PASSWORD: gym
      POSTGRES_DB: gym_backend
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gym -d gym_backend"]
      interval: 5s
      timeout: 5s
      retries: 5

  app:
    build: .
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://gym:gym@postgres:5432/gym_backend
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"

volumes:
  postgres_data:
```

- [ ] **Step 3: Verify the full stack boots**

```bash
docker compose up --build -d
docker compose logs -f app
```
Expected: logs show `Uvicorn running on http://0.0.0.0:8000`

```bash
curl -s http://localhost:8000/health
```
Expected: `{"status":"ok"}`

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .dockerignore docker-compose.yml
git commit -m "feat: containerize app and postgres with Docker Compose"
```

---

### Task 11: Generate docs/spec.md

**Files:**
- Create: `docs/spec.md`

**Interfaces:**
- Consumes: every prior task's endpoints, env vars, and run commands — this task only documents, no code changes.

- [ ] **Step 1: Write the spec document**

`docs/spec.md`:
```markdown
# Backend Spec

## Environment Variables

| Key | Description | Example |
|---|---|---|
| `ENV` | Environment name: `local`, `dev`, or `prod`. Controls SQL echo logging. | `local` |
| `DATABASE_URL` | Async Postgres connection string (`postgresql+asyncpg://` scheme). | `postgresql+asyncpg://gym:gym@localhost:5432/gym_backend` |
| `SECRET_KEY` | HMAC signing key for JWTs. Must be random and secret in `dev`/`prod`. | `change-me-to-a-random-secret` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime in minutes. | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime in days. | `7` |
| `OTP_EXPIRE_MINUTES` | OTP code lifetime in minutes. | `10` |

## Auth Flows

### Admin login
`POST /admin/auth/login` — `{ email, password }` → `200 { access_token, refresh_token, token_type }` / `401` invalid credentials / `403` account disabled.

### Admin logout
`POST /admin/auth/logout` — Header `Authorization: Bearer <access_token>`, body `{ refresh_token }` → `200 { message }`. Revokes the refresh token server-side.

### Admin password recovery
Two-step: `POST /admin/auth/password-recovery/request` — `{ email }` → always `200` (doesn't leak whether the email exists), sends an OTP via `app.utils.email.send_otp_email` (logs the code in this scaffold). `POST /admin/auth/password-recovery/confirm` — `{ email, otp_code, new_password }` → `200 { message }` / `400` invalid or expired OTP. No password-strength rule for admins.

### Admin OTP verify
`POST /admin/auth/otp/verify` — `{ email, otp_code }` → `200 { access_token, refresh_token, token_type }` / `400` invalid or expired OTP. Consumes an OTP with `purpose="login_otp"` created via `auth_service.create_otp`.

### User registration
`POST /auth/register` — `{ email, password }` → `201 { access_token, refresh_token, token_type }` / `400` weak password / `409` email already registered. Password-strength rules enforced.

### User login / logout / OTP verify
Same shapes as the admin flows, under `/auth/*` instead of `/admin/auth/*`.

### User password recovery
Same two-step shape as admin, under `/auth/password-recovery/*`. Password-strength rules enforced on `new_password`.

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
| POST | `/admin/auth/otp/verify` | No | Verify a login OTP, get tokens |
| POST | `/auth/register` | No | Register a new end-user account |
| POST | `/auth/login` | No | User login |
| POST | `/auth/logout` | Bearer (user) | Revoke a refresh token |
| POST | `/auth/password-recovery/request` | No | Request a password-recovery OTP |
| POST | `/auth/password-recovery/confirm` | No | Confirm OTP + set new password |
| POST | `/auth/otp/verify` | No | Verify a login OTP, get tokens |
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

- **Access token**: JWT, HS256, `ACCESS_TOKEN_EXPIRE_MINUTES` lifetime. Claims: `sub` (principal UUID as string), `exp`.
- **Refresh token**: JWT, HS256, `REFRESH_TOKEN_EXPIRE_DAYS` lifetime. Claims: `sub`, `exp`, `type: "refresh"`. Also stored server-side (SHA-256 hash) in `refresh_tokens` so it can be revoked or rotated independent of the JWT's own expiry.
- **Where to send them**: access token in `Authorization: Bearer <access_token>` header on protected endpoints (`/admin/auth/logout`, `/auth/logout`). Refresh token goes in the request body for `/auth/token/refresh` and the `logout` endpoints.
```

- [ ] **Step 2: Review the document covers every required section**

Confirm `docs/spec.md` has all five required sections: environment variables table, auth flows, endpoints table, run commands, JWT details. (It does, per Step 1.)

- [ ] **Step 3: Commit**

```bash
git add docs/spec.md
git commit -m "docs: add backend spec (env vars, auth flows, endpoints, run commands)"
```

---

## Final Verification

After Task 11, run the full suite one more time end-to-end:
```bash
docker compose up -d postgres
alembic upgrade head
pytest -v
docker compose up --build -d
curl -s http://localhost:8000/health
```
Expected: all tests pass, health check returns `{"status":"ok"}`.
