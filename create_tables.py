"""Create all database tables from SQLAlchemy models."""
import asyncio
from nabr.db.session import engine, Base
from nabr.models import *  # noqa: F403, F401


async def create_tables():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All tables created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tables())
