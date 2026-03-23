from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.rag.generator import get_llm
import json

async def get_knowledge_state(
    db: AsyncSession,
    user_id: str
) -> dict:
    """Get all concept confidence scores for a user."""
    result = await db.execute(
        text("""
            SELECT concept, confidence_score, times_practiced, last_error
            FROM user_knowledge_state
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    )
    rows = result.fetchall()
    return {
        r.concept: {
            "confidence": r.confidence_score,
            "practiced": r.times_practiced,
            "last_error": r.last_error
        }
        for r in rows
    }


async def get_adaptive_recommendation(
    db: AsyncSession,
    user_id: str,
    course_id: str
) -> dict:
    """
    Analyze user performance and recommend next steps.
    If confidence < 0.6 on any concept → suggest remedial.
    If confidence > 0.9 → suggest skipping ahead.
    """
    knowledge = await get_knowledge_state(db, user_id)

    struggling = [
        concept for concept, data in knowledge.items()
        if data["confidence"] < 0.6
    ]
    mastered = [
        concept for concept, data in knowledge.items()
        if data["confidence"] >= 0.9
    ]

    recommendations = []

    if struggling:
        recommendations.append({
            "type": "remedial",
            "message": f"You need more practice on: {', '.join(struggling)}",
            "concepts": struggling,
            "action": "Review these concepts before moving forward"
        })

    if mastered:
        recommendations.append({
            "type": "advance",
            "message": f"You've mastered: {', '.join(mastered)}",
            "concepts": mastered,
            "action": "You can move ahead faster on these topics"
        })

    if not struggling and not mastered:
        recommendations.append({
            "type": "on_track",
            "message": "You're progressing well! Keep going.",
            "action": "Continue with the current plan"
        })

    return {
        "user_id": user_id,
        "knowledge_state": knowledge,
        "recommendations": recommendations,
        "needs_remedial": len(struggling) > 0
    }


def inject_knowledge_into_prompt(
    knowledge_state: dict,
    base_prompt: str
) -> str:
    """
    Inject user's knowledge state into the chatbot prompt
    so the LLM knows what the user struggles with.
    """
    if not knowledge_state:
        return base_prompt

    struggling = [
        concept for concept, data in knowledge_state.items()
        if data["confidence"] < 0.6
    ]
    strong = [
        concept for concept, data in knowledge_state.items()
        if data["confidence"] >= 0.8
    ]

    knowledge_context = "\nUSER KNOWLEDGE PROFILE:"

    if struggling:
        knowledge_context += f"\n- Struggling with: {', '.join(struggling)}"
        knowledge_context += "\n  → Explain these topics more carefully with examples"

    if strong:
        knowledge_context += f"\n- Already knows well: {', '.join(strong)}"
        knowledge_context += "\n  → No need to over-explain these"

    # Inject after system prompt, before context
    return base_prompt.replace(
        "CONTEXT:",
        f"{knowledge_context}\n\nCONTEXT:"
    )