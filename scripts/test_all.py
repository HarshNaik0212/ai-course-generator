"""
End-to-end test script for all API flows.
Run with: python scripts/test_all.py
"""
import httpx
import asyncio
import json

BASE_URL = "http://localhost:8000"
USER_ID = "test-user-e2e"

async def test_health():
    print("\n🔍 Testing Health...")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["postgres"] == "connected"
        assert data["redis"] == "connected"
    print("✅ Health check passed")


async def test_ingest():
    print("\n🔍 Testing Document Ingestion...")
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/api/docs/ingest", json={
            "title": "Python Basics Test",
            "content": """Python is a high-level programming language.
            Functions are defined using the def keyword.
            Variables store data values. Lists store multiple items.
            Loops repeat code. If statements make decisions.""",
            "doc_type": "article",
            "topic": "python"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] == True
        assert data["chunks_created"] >= 1
    print(f"✅ Ingestion passed — {data['chunks_created']} chunks created")


async def test_search():
    print("\n🔍 Testing Hybrid Search...")
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/api/docs/search", json={
            "query": "how to define a function",
            "top_k": 3
        })
        assert r.status_code == 200
        data = r.json()
        assert data["results_count"] >= 0
    print(f"✅ Search passed — {data['results_count']} results found")


async def test_chat():
    print("\n🔍 Testing Chat (streaming)...")
    tokens = []
    session_id = None

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", f"{BASE_URL}/api/chat", json={
            "user_id": USER_ID,
            "message": "What is a Python function?"
        }) as r:
            assert r.status_code == 200
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "token" in data:
                        tokens.append(data["token"])
                    if "done" in data:
                        session_id = data.get("session_id")

    assert len(tokens) > 0, "No tokens received"
    answer = "".join(tokens)
    assert len(answer) > 20, "Answer too short"
    print(f"✅ Chat passed — {len(tokens)} tokens, session: {session_id}")
    return session_id


async def test_course_generation():
    print("\n🔍 Testing Course Generation (takes 30-60s)...")
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{BASE_URL}/api/courses/generate", json={
            "user_id": USER_ID,
            "topic": "Python Basics",
            "skill_level": "beginner",
            "hours_per_day": 1,
            "duration_weeks": 1,
            "goals": ["learn basics"]
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] == True
        assert data["course_id"] is not None
        course_id = data["course_id"]

    print(f"✅ Course generation passed — ID: {course_id}")
    return course_id


async def test_get_course(course_id: str):
    print("\n🔍 Testing Get Course...")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/api/courses/{course_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["course_id"] == course_id
        assert len(data["week_plans"]) > 0
    print(f"✅ Get course passed — {len(data['week_plans'])} weeks")


async def test_get_quiz(course_id: str):
    print("\n🔍 Testing Get Quiz...")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/api/courses/{course_id}/quiz")
        assert r.status_code == 200
        data = r.json()
        assert data["total_questions"] > 0
        question_id = data["questions"][0]["id"]
    print(f"✅ Quiz passed — {data['total_questions']} questions")
    return question_id


async def test_submit_answer(question_id: str):
    print("\n🔍 Testing Quiz Submit...")
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{BASE_URL}/api/courses/quiz/submit", json={
            "user_id": USER_ID,
            "question_id": question_id,
            "user_answer": "A"
        })
        assert r.status_code == 200
        data = r.json()
        assert "is_correct" in data
        assert "explanation" in data
    print(f"✅ Submit answer passed — correct: {data['is_correct']}")


async def test_progress(course_id: str):
    print("\n🔍 Testing Progress...")
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{BASE_URL}/api/courses/{course_id}/progress/{USER_ID}"
        )
        assert r.status_code == 200
        data = r.json()
        assert "completion_percentage" in data
    print(f"✅ Progress passed — {data['completion_percentage']}% complete")


async def test_adaptive(course_id: str):
    print("\n🔍 Testing Adaptive Recommendations...")
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{BASE_URL}/api/courses/{course_id}/adaptive/{USER_ID}"
        )
        assert r.status_code == 200
        data = r.json()
        assert "recommendations" in data
    print(f"✅ Adaptive passed — {len(data['recommendations'])} recommendations")


async def run_all_tests():
    print("=" * 50)
    print("🚀 AI COURSE GENERATOR — END TO END TESTS")
    print("=" * 50)

    try:
        await test_health()
        await test_ingest()
        await test_search()
        await test_chat()
        course_id = await test_course_generation()
        await test_get_course(course_id)
        question_id = await test_get_quiz(course_id)
        await test_submit_answer(question_id)
        await test_progress(course_id)
        await test_adaptive(course_id)

        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n💥 ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(run_all_tests())