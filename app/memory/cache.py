from app.db.redis import redis_client
from app.rag.embedder import embedder
import json
import hashlib
import logging
import numpy as np

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.97
CACHE_TTL = 3600       # 1 hour
MAX_CACHE_ENTRIES = 1000


def cosine_similarity(a: list, b: list) -> float:
    """Calculate cosine similarity between two vectors."""
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    dot = np.dot(a_arr, b_arr)
    norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if norm == 0:
        return 0.0
    return float(dot / norm)


async def get_cached_response(query: str) -> str | None:
    """
    Phase 2 Semantic Cache:
    1. Embed the query
    2. Compare against all cached query embeddings
    3. If similarity > 0.97, return cached response instantly
    """
    try:
        query_embedding = await embedder.aembed(query)

        # Get all cached keys
        keys = await redis_client.keys("cache:entry:*")
        if not keys:
            return None

        # Check similarity against all cached queries
        best_similarity = 0.0
        best_response = None

        for key in keys[:MAX_CACHE_ENTRIES]:
            cached_data = await redis_client.get(key)
            if not cached_data:
                continue
            try:
                entry = json.loads(cached_data)
                cached_embedding = entry["embedding"]
                similarity = cosine_similarity(query_embedding, cached_embedding)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_response = entry["response"]
            except Exception:
                continue

        if best_similarity >= SIMILARITY_THRESHOLD and best_response:
            logger.info(f"Cache HIT (similarity: {best_similarity:.3f})")
            return best_response

        logger.info(f"Cache MISS (best similarity: {best_similarity:.3f})")
        return None

    except Exception as e:
        logger.warning(f"Cache lookup failed: {e}")
        return None


async def set_cached_response(query: str, response: str):
    """Save query + embedding + response to Redis."""
    try:
        query_embedding = await embedder.aembed(query)
        cache_key = f"cache:entry:{hashlib.md5(query.encode()).hexdigest()}"

        entry = {
            "query": query,
            "embedding": query_embedding,
            "response": response
        }
        await redis_client.setex(
            cache_key,
            CACHE_TTL,
            json.dumps(entry)
        )
        logger.info(f"Cache SET for query: {query[:50]}...")

    except Exception as e:
        logger.warning(f"Cache save failed: {e}")


async def get_session_context(session_id: str) -> dict | None:
    key = f"session:{session_id}"
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return None


async def set_session_context(session_id: str, context: dict, ttl: int = 86400):
    key = f"session:{session_id}"
    await redis_client.setex(key, ttl, json.dumps(context))