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
