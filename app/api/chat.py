from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from app.db.postgres import get_db
from app.rag.retriever import hybrid_retrieve
from app.rag.generator import get_llm, build_rag_prompt
from app.memory.history import get_recent_history, save_message
from app.memory.cache import get_cached_response, set_cached_response
from app.adaptive.learning_engine import get_knowledge_state
import uuid
import json

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
            cached = await get_cached_response(request.message)
            if cached:
                yield f"data: {json.dumps({'token': cached})}\n\n"
                yield f"data: {json.dumps({'done': True, 'session_id': session_id, 'cached': True})}\n\n"
                return

            # Step 4 — Load history + knowledge state (parallel)
            history = await get_recent_history(db, session_id, limit=10)
            knowledge = await get_knowledge_state(db, user_id)

            # Step 5 — Retrieve context
            chunks = await hybrid_retrieve(db, request.message, top_k=5)

            # Step 6 — Build adaptive prompt
            prompt = build_rag_prompt(
                question=request.message,
                context_chunks=chunks,
                conversation_history=history,
                knowledge_state=knowledge      # ← injected!
            )

            # Step 7 — Stream response
            llm = get_llm(streaming=True)
            full_answer = ""

            async for chunk in llm.astream(prompt):
                token = chunk.content
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