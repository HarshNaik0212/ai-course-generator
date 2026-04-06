"""
Test RAPTOR + Contextual RAG ingestion pipeline.
Run: python scripts/test_raptor_contextual.py
"""
import httpx
import asyncio
import json

BASE_URL = "http://localhost:8000"


async def test_ingest_pdf():
    print("🔍 Testing PDF ingestion with RAPTOR + Contextual RAG...")
    
    with open("lbdl.pdf", "rb") as f:
        pdf_bytes = f.read()

    async with httpx.AsyncClient(timeout=300) as client:  # 5 min timeout
        response = await client.post(
            f"{BASE_URL}/api/docs/ingest-pdf",
            files={"file": ("lbdl.pdf", pdf_bytes, "application/pdf")},
            data={"title": "Little Book of Deep Learning", "topic": "deep learning"}
        )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Ingestion successful!")
        print(f"   Document ID:    {data['document_id']}")
        print(f"   Level 0 chunks: {data['level0_chunks']}")
        print(f"   RAPTOR stats:   {json.dumps(data['raptor'], indent=2)}")
        print(f"   Contextual RAG: {data['contextual_rag']}")
        print(f"   Pages:          {data['pages_processed']}")
        return data['document_id']
    else:
        print(f"❌ Failed: {response.text}")
        return None


async def test_search_levels(doc_id: str):
    """Test that all RAPTOR levels are retrievable."""
    print("\n🔍 Testing retrieval across RAPTOR levels...")

    queries = [
        ("broad", "overview of deep learning"),
        ("specific", "backpropagation gradient computation"),
        ("technical", "convolutional neural network architecture"),
    ]

    async with httpx.AsyncClient(timeout=30) as client:
        for query_type, query in queries:
            r = await client.post(f"{BASE_URL}/api/docs/search", json={
                "query": query,
                "top_k": 5
            })
            data = r.json()
            print(f"\n   Query ({query_type}): '{query}'")
            print(f"   Results: {data['results_count']}")
            for result in data['results'][:2]:
                print(f"   → [{result.get('topic', 'N/A')}] {result['content'][:100]}...")


async def run_tests():
    print("=" * 60)
    print("🚀 RAPTOR + CONTEXTUAL RAG — PIPELINE TEST")
    print("=" * 60)

    try:
        doc_id = await test_ingest_pdf()
        if doc_id:
            await test_search_levels(doc_id)
            print("\n" + "=" * 60)
            print("🎉 RAPTOR + Contextual RAG working!")
            print("=" * 60)
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_tests())