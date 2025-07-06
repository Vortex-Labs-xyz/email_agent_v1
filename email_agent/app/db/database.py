from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from ..core.config import settings
import asyncio


# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True
)

# Create async session maker
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncSession:
    """Get async database session."""
    async with async_session() as session:
        yield session


class DatabaseManager:
    """Database manager for handling database operations."""
    
    def __init__(self):
        self.engine = engine
        self.session_maker = async_session
    
    async def create_tables(self):
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
    
    async def get_session(self) -> AsyncSession:
        """Get database session."""
        async with self.session_maker() as session:
            yield session
    
    async def close(self):
        """Close database connection."""
        await self.engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()