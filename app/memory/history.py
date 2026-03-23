from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.rag.embedder import embedder
import uuid

async def save_message(
    db: AsyncSession,
    user_id: str,
    session_id: str,
    role: str,          # 'user' or 'assistant'
    content: str,
    course_id: str = None
):
    """Save a single message to conversation history."""
    msg_id = str(uuid.uuid4())

    # Embed the message for future semantic search
    embedding = await embedder.aembed(content)
    embedding_str = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"

    await db.execute(
        text("""
            INSERT INTO conversations
                (id, user_id, session_id, role, content, embedding, course_id)
            VALUES
                (:id, :user_id, :session_id, :role, :content,
                 CAST(:embedding AS vector), :course_id)
        """),
        {
            "id": msg_id,
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "embedding": embedding_str,
            "course_id": course_id
        }
    )
    await db.commit()


async def get_recent_history(
    db: AsyncSession,
    session_id: str,
    limit: int = 10
) -> list:
    """Get last N messages for a session."""
    result = await db.execute(
        text("""
            SELECT role, content, created_at
            FROM conversations
            WHERE session_id = :session_id
            ORDER BY created_at ASC
            LIMIT :limit
        """),
        {"session_id": session_id, "limit": limit}
    )
    rows = result.fetchall()
    return [{"role": row.role, "content": row.content} for row in rows]


async def search_past_conversations(
    db: AsyncSession,
    user_id: str,
    query: str,
    top_k: int = 3
) -> list:
    """Find semantically similar past messages for context injection."""
    query_embedding = await embedder.aembed(query)
    embedding_str = "[" + ",".join(f"{x:.8f}" for x in query_embedding) + "]"

    result = await db.execute(
        text("""
            SELECT role, content,
                1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM conversations
            WHERE user_id = :user_id
                AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """),
        {
            "embedding": embedding_str,
            "user_id": user_id,
            "top_k": top_k
        }
    )
    rows = result.fetchall()
    return [
        {"role": row.role, "content": row.content, "similarity": float(row.similarity)}
        for row in rows
    ]