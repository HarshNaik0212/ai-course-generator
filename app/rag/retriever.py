from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.rag.embedder import embedder
from app.rag.hyde import get_hyde_embedding, decompose_query
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


async def vector_search(
    db: AsyncSession,
    query_embedding: list,
    top_k: int = 20
) -> List[Dict]:
    """Dense vector search using pgvector cosine similarity."""
    embedding_str = "[" + ",".join(f"{x:.8f}" for x in query_embedding) + "]"

    level_filter = None
    level_clause = f"AND c.level = {level_filter}" if level_filter is not None else ""

    result = await db.execute(
        text("""
            SELECT
                c.id,
                c.content,
                c.chunk_index,
                c.level,
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
            "level": row.level,
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
    """BM25 search using pg_search (ParadeDB)."""
    try:
        result = await db.execute(
            text("""
                SELECT
                    c.id,
                    c.content,
                    c.chunk_index,
                    c.level,
                    d.title,
                    d.topic,
                    paradedb.score(c.id) AS score
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.id @@@ paradedb.match('content', :query)
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
                "level": row.level,
                "score": float(row.score),
                "source": "bm25"
            }
            for row in rows
        ]
    except Exception as e:
        logger.warning(f"BM25 search failed, falling back to GIN: {e}")
        # Fallback to GIN full-text if pg_search fails
        result = await db.execute(
            text("""
                SELECT c.id, c.content, c.chunk_index, c.level,
                       d.title, d.topic,
                       ts_rank(to_tsvector('english', c.content),
                               plainto_tsquery('english', :query)) AS score
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
                "level": row.level,
                "score": float(row.score),
                "source": "gin_fallback"
            }
            for row in rows
        ]


def reciprocal_rank_fusion(
    vector_results: List[Dict],
    keyword_results: List[Dict],
    k: int = 60
) -> List[Dict]:
    """RRF: score = 1 / (k + rank). Merges vector and keyword results."""
    fused: Dict[str, Dict] = {}

    for rank, doc in enumerate(vector_results):
        doc_id = doc["id"]
        if doc_id not in fused:
            fused[doc_id] = {**doc, "rrf_score": 0.0}
        fused[doc_id]["rrf_score"] += 1.0 / (k + rank + 1)

    for rank, doc in enumerate(keyword_results):
        doc_id = doc["id"]
        if doc_id not in fused:
            fused[doc_id] = {**doc, "rrf_score": 0.0}
        fused[doc_id]["rrf_score"] += 1.0 / (k + rank + 1)

    return sorted(fused.values(), key=lambda x: x["rrf_score"], reverse=True)


async def hybrid_retrieve(
    db: AsyncSession,
    query: str,
    top_k: int = 10,
    use_hyde: bool = True,
    use_decomposition: bool = True
) -> List[Dict]:
    """
    Full Phase 2 retrieval:
    1. Query Decomposition → multiple sub-queries
    2. HyDE → hypothetical answer embedding
    3. Hybrid search (vector + BM25) for each sub-query
    4. Merge all results with RRF
    Returns top_k candidates for reranker
    """
    all_vector_results = []
    all_keyword_results = []

    # Step 1 — Query Decomposition
    if use_decomposition:
        sub_queries = await decompose_query(query)
    else:
        sub_queries = [query]

    logger.info(f"Retrieving for {len(sub_queries)} queries")

    # Step 2 — For each sub-query, run hybrid search
    # Run sequentially to avoid DB session concurrency issues
    for q in sub_queries:
        # HyDE embedding for vector search
        if use_hyde:
            hyde_embedding = await get_hyde_embedding(q)
        else:
            hyde_embedding = await embedder.aembed(q)

        v_results = await vector_search(db, hyde_embedding, top_k=20)
        k_results = await keyword_search(db, q, top_k=20)
        
        all_vector_results.extend(v_results)
        all_keyword_results.extend(k_results)

    # Step 3 — RRF fusion of all results
    fused = reciprocal_rank_fusion(all_vector_results, all_keyword_results)

    # Return top 60 for reranker (or top_k if no reranker)
    return fused[:60]