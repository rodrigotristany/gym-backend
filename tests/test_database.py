from sqlalchemy import text

from app.database import engine


async def test_engine_connects_to_database():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
