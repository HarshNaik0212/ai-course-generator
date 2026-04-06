from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from app.db.postgres import get_db
from app.rag.retriever import hybrid_retrieve
from app.memory.history import get_recent_history, save_message
from app.memory.cache import get_cached_response, set_cached_response
from app.adaptive.learning_engine import get_knowledge_state
import uuid
import json
from app.rag.generator import stream_llm, build_rag_prompt


router = APIRouter()

class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    message: str
    course_id: Optional[str] = None


@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    # Step 1 — Fix IDs
    session_id = request.session_id or str(uuid.uuid4())
    try:
        uuid.UUID(request.user_id)
        user_id = request.user_id
    except ValueError:
        user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, request.user_id))

    # Step 2 — Auto-create user
    await db.execute(
        text("""
            INSERT INTO users (id, email, name)
            VALUES (:id, :email, :name)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id": user_id,
            "email": f"{request.user_id}@temp.com",
            "name": request.user_id
        }
    )
    await db.commit()

    async def event_generator():
        try:
            # Step 3 — Check Redis cache first
            yield f"data: {json.dumps({'status': 'checking_cache'})}\n\n"
            cached = await get_cached_response(request.message)
            if cached:
                yield f"data: {json.dumps({'token': cached})}\n\n"
                yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'cached': True})}\n\n"
                return

            # Step 4 — Load history + knowledge state (parallel)
            yield f"data: {json.dumps({'status': 'loading_context'})}\n\n"
            history = await get_recent_history(db, session_id, limit=10)
            knowledge = await get_knowledge_state(db, user_id)

            # Step 5 — Retrieve + Rerank
            yield f"data: {json.dumps({'status': 'retrieving'})}\n\n"
            chunks_candidates = await hybrid_retrieve(
                db, request.message, top_k=60,
                use_hyde=True,
                use_decomposition=True
            )
            # Rerank top 60 → top 10
            yield f"data: {json.dumps({'status': 'reranking'})}\n\n"
            from app.rag.reranker import reranker  # Lazy import to avoid blocking startup
            chunks = await reranker.rerank(
                query=request.message,
                chunks=chunks_candidates,
                top_k=10
            )

            # Step 6 — Build adaptive prompt
            prompt = build_rag_prompt(
                question=request.message,
                context_chunks=chunks,
                conversation_history=history,
                knowledge_state=knowledge      # ← injected!
            )

            # Step 7 — Stream response
            full_answer = ""
            yield f"data: {json.dumps({'status': 'generating'})}\n\n"

            async for token in stream_llm(prompt):
                if token:
                    full_answer += token
                    yield f"data: {json.dumps({'token': token})}\n\n"

            # Step 8 — Save to memory + cache
            await save_message(db, user_id, session_id, "user", request.message)
            await save_message(db, user_id, session_id, "assistant", full_answer)
            await set_cached_response(request.message, full_answer)

            yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@router.get("/chat/history/{session_id}")
async def get_history(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    history = await get_recent_history(db, session_id, limit=50)
    return {"session_id": session_id, "messages": history}