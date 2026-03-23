from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.rag.embedder import embedder
from typing import List, Dict

async def vector_search(
    db: AsyncSession,
    query_embedding: list,
    top_k: int = 20
) -> List[Dict]:
    """Dense vector search using pgvector cosine similarity."""
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    result = await db.execute(
        text("""
            SELECT
                c.id,
                c.content,
                c.chunk_index,
                d.title,
                d.topic,
                1 - (c.dense_embedding <=> CAST(:embedding AS vector)) AS score
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.dense_embedding IS NOT NULL
            ORDER BY c.dense_embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """),
        {"embedding": embedding_str, "top_k": top_k}
    )
    rows = result.fetchall()
    return [
        {
            "id": str(row.id),
            "content": row.content,
            "title": row.title,
            "topic": row.topic,
            "score": float(row.score),
            "source": "vector"
        }
        for row in rows
    ]


async def keyword_search(
    db: AsyncSession,
    query: str,
    top_k: int = 20
) -> List[Dict]:
    """BM25-style keyword search using PostgreSQL full-text search."""
    result = await db.execute(
        text("""
            SELECT
                c.id,
                c.content,
                c.chunk_index,
                d.title,
                d.topic,
                ts_rank(
                    to_tsvector('english', c.content),
                    plainto_tsquery('english', :query)
                ) AS score
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE to_tsvector('english', c.content)
                  @@ plainto_tsquery('english', :query)
            ORDER BY score DESC
            LIMIT :top_k
        """),
        {"query": query, "top_k": top_k}
    )
    rows = result.fetchall()
    return [
        {
            "id": str(row.id),
            "content": row.content,
            "title": row.title,
            "topic": row.topic,
            "score": float(row.score),
            "source": "keyword"
        }
        for row in rows
    ]


def reciprocal_rank_fusion(
    vector_results: List[Dict],
    keyword_results: List[Dict],
    k: int = 60
) -> List[Dict]:
    """
    RRF formula: score = 1 / (k + rank)
    Merges vector and keyword results into one ranked list.
    """
    fused: Dict[str, Dict] = {}

    # Score vector results
    for rank, doc in enumerate(vector_results):
        doc_id = doc["id"]
        if doc_id not in fused:
            fused[doc_id] = {**doc, "rrf_score": 0.0}
        fused[doc_id]["rrf_score"] += 1.0 / (k + rank + 1)

    # Score keyword results
    for rank, doc in enumerate(keyword_results):
        doc_id = doc["id"]
        if doc_id not in fused:
            fused[doc_id] = {**doc, "rrf_score": 0.0}
        fused[doc_id]["rrf_score"] += 1.0 / (k + rank + 1)

    # Sort by fused score
    sorted_results = sorted(
        fused.values(),
        key=lambda x: x["rrf_score"],
        reverse=True
    )
    return sorted_results


async def hybrid_retrieve(
    db: AsyncSession,
    query: str,
    top_k: int = 10
) -> List[Dict]:
    """
    Full hybrid retrieval pipeline:
    1. Embed query
    2. Vector search (top 20)
    3. Keyword search (top 20)
    4. RRF fusion → return top_k
    """
    # Embed query
    query_embedding = await embedder.aembed(query)

    # Run both searches
    vector_results  = await vector_search(db, query_embedding, top_k=20)
    keyword_results = await keyword_search(db, query, top_k=20)

    # Fuse and return top_k
    fused = reciprocal_rank_fusion(vector_results, keyword_results)
    return fused[:top_k]