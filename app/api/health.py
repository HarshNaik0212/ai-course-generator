from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.postgres import get_db
from app.db.redis import redis_client

router = APIRouter()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    # Check PostgreSQL
    await db.execute(text("SELECT 1"))

    # Check Redis
    await redis_client.ping()

    return {
        "status": "ok",
        "postgres": "connected",
        "redis": "connected"
    }