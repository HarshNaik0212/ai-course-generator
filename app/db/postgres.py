from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings

# Configure connection pool: 5-20 connections with proper cleanup
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,          # Maximum persistent connections in pool
    max_overflow=10,       # Extra connections allowed when pool is full
    pool_timeout=30,       # Seconds to wait before timing out on connection request
    pool_recycle=1800,     # Recycle connections every 30 minutes
    pool_pre_ping=True,    # Test connection health before using
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session