"""
Day 3 Pipeline Test — Retrieval + Reranker + Cache
Run: python scripts/test_day3_pipeline.py
   OR: pytest scripts/test_day3_pipeline.py -v
"""
import asyncio
import httpx
import json
import time
import pytest

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_retrieval_pipeline():
    print("\n🔍 Testing full retrieval pipeline...")
    queries = [
        "explain backpropagation in neural networks",
        "what is gradient descent",
        "how does a CNN work",
    ]

    async with httpx.AsyncClient(timeout=120) as client:
        for query in queries:
            start = time.time()
            r = await client.post(f"{BASE_URL}/api/docs/search", json={
                "query": query,
                "top_k": 5
            })
            elapsed = time.time() - start
            data = r.json()
            print(f"\n   Query: '{query}'")
            print(f"   Response keys: {list(data.keys())}")
            print(f"   Status: {r.status_code}")
            if "detail" in data:
                print(f"   ❌ Error: {data['detail']}")
                raise Exception(f"Server error: {data['detail']}")
            print(f"   Results: {data['results_count']} | Time: {elapsed:.2f}s")
            for res in data["results"][:2]:
                print(f"   → [L{res.get('level',0)}] {res['content'][:80]}...")


@pytest.mark.asyncio
async def test_cache():
    print("\n🔍 Testing semantic cache...")

    # Q1 is a completely new question (will be cached as a miss)
    # Q2 matches the already-cached "can you explain neural networks?" from earlier runs
    query1 = "what is overfitting in machine learning?"
    query2 = "can you explain neural networks?"  # Already cached from previous run

    # Use Timeout with high read_timeout for streaming (first token can take 15+ seconds)
    timeout = httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=120.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # First chat — NEW question (cache MISS, will be stored)
        start = time.time()
        tokens1 = []
        async with client.stream("POST", f"{BASE_URL}/api/chat", json={
            "user_id": "cache-test-user",
            "message": query1
        }, timeout=180) as r:
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "token" in data:
                        tokens1.append(data["token"])
        time1 = time.time() - start
        print(f"\n   Q1 (miss - new): {len(tokens1)} tokens in {time1:.2f}s")

        # Second chat — should be CACHE HIT (matches cached query)
        start = time.time()
        tokens2 = []
        async with client.stream("POST", f"{BASE_URL}/api/chat", json={
            "user_id": "cache-test-user",
            "message": query2
        }, timeout=180) as r:
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "token" in data:
                        tokens2.append(data["token"])
                    if data.get("cached"):
                        print(f"   ✅ Cache HIT!")
        time2 = time.time() - start
        print(f"   Q2 (hit - cached): {len(tokens2)} tokens in {time2:.2f}s")
        print(f"   Speedup: {time1/max(time2,0.1):.1f}x faster")


async def run_tests():
    print("=" * 60)
    print("🚀 DAY 3 — RETRIEVAL PIPELINE TEST")
    print("=" * 60)

    try:
        await test_retrieval_pipeline()
        await test_cache()
        print("\n" + "=" * 60)
        print("🎉 Day 3 pipeline working!")
        print("=" * 60)
    except Exception as e:
        import traceback
        print(f"\n💥 ERROR: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_tests())