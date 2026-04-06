"""
Test pgvector retrieval — checks if chunks with dense_embedding exist
and can be retrieved via cosine similarity search.
Run: python scripts/test_pgvector_retrieval.py
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from app.db.postgres import AsyncSessionLocal
from app.rag.embedder import embedder
from app.rag.retriever import vector_search, keyword_search


async def test_pgvector_store():
    print("=" * 60)
    print("🧪 PGVECTOR RETRIEVAL TEST")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # Step 1 — Check if chunks with embeddings exist
        print("\n📊 Checking chunks with dense_embedding...")
        result = await db.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(dense_embedding) as with_embedding,
                   COUNT(*) FILTER (WHERE dense_embedding IS NOT NULL) as not_null
            FROM chunks
        """))
        row = result.fetchone()
        print(f"   Total chunks: {row.total}")
        print(f"   With embedding column: {row.with_embedding}")
        print(f"   NOT NULL embeddings: {row.not_null}")

        if row.not_null == 0:
            print("\n❌ No chunks have dense_embedding values!")
            return False

        # Step 2 — Check embedding dimension (query embedding to compare)
        print("\n📏 Preparing test query embedding...")
        test_query = "explain backpropagation in neural networks"
        query_embedding = await embedder.aembed(test_query)
        print(f"   Query embedding dimension: {len(query_embedding)}")

        # Step 3 — Check documents linked to chunks
        print("\n📁 Checking linked documents...")
        result = await db.execute(text("""
            SELECT d.id, d.title, COUNT(c.id) as chunk_count
            FROM documents d
            LEFT JOIN chunks c ON c.document_id = d.id
            WHERE c.dense_embedding IS NOT NULL
            GROUP BY d.id, d.title
            ORDER BY chunk_count DESC
            LIMIT 5
        """))
        docs = result.fetchall()
        if docs:
            for doc in docs:
                print(f"   → {doc.title} ({doc.chunk_count} chunks)")
        else:
            print("   ⚠ No documents linked to chunks with embeddings")

        # Step 4 — Test vector search
        print("\n🔍 Testing vector search...")
        print(f"   Query: '{test_query}'")

        # Search
        print("   Searching pgvector store...")
        results = await vector_search(db, query_embedding, top_k=5)

        if results:
            print(f"\n✅ Retrieved {len(results)} results!")
            for i, res in enumerate(results[:3], 1):
                print(f"\n   [{i}] Score: {res['score']:.4f} | Level: L{res['level']}")
                print(f"       Title: {res['title']}")
                print(f"       Content: {res['content'][:120]}...")
        else:
            print("\n❌ No results found!")
            return False

        # Step 5 — Test keyword search
        print("\n🔍 Testing keyword search...")
        kw_results = await keyword_search(db, test_query, top_k=5)
        print(f"   Retrieved {len(kw_results)} results (source: {kw_results[0]['source'] if kw_results else 'none'})")

        # Step 6 — Check score distribution
        if results:
            print("\n📊 Score distribution:")
            scores = [r['score'] for r in results]
            print(f"   Min: {min(scores):.4f} | Max: {max(scores):.4f} | Avg: {sum(scores)/len(scores):.4f}")

    print("\n" + "=" * 60)
    print("🎉 pgvector retrieval working!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_pgvector_store())
    sys.exit(0 if success else 1)
