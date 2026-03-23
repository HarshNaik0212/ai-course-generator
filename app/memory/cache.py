from app.db.redis import redis_client
from app.rag.embedder import embedder
import json
import hashlib

# Simple exact-match cache for MVP
# Phase 2: upgrade to semantic similarity cache

async def get_cached_response(query: str) -> str | None:
    """Check Redis for an exact cached response."""
    # Create a hash key from the query
    key = f"chat:cache:{hashlib.md5(query.lower().strip().encode()).hexdigest()}"
    cached = await redis_client.get(key)
    if cached:
        print(f"Cache HIT for query: {query[:50]}...")
        return cached
    return None


async def set_cached_response(
    query: str,
    response: str,
    ttl_seconds: int = 3600    # cache for 1 hour
):
    """Save response to Redis cache."""
    key = f"chat:cache:{hashlib.md5(query.lower().strip().encode()).hexdigest()}"
    await redis_client.setex(key, ttl_seconds, response)
    print(f"Cache SET for query: {query[:50]}...")


async def get_session_context(session_id: str) -> dict | None:
    """Get session data from Redis (fast access)."""
    key = f"session:{session_id}"
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return None


async def set_session_context(
    session_id: str,
    context: dict,
    ttl_seconds: int = 86400   # 24 hours
):
    """Save session context to Redis."""
    key = f"session:{session_id}"
    await redis_client.setex(key, ttl_seconds, json.dumps(context))