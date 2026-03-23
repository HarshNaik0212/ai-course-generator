from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

async def mark_day_complete(
    db: AsyncSession,
    week_plan_id: str,
    day_number: int
):
    """Mark a specific day as completed."""
    await db.execute(
        text("""
            UPDATE day_plans
            SET is_completed = TRUE, completed_at = NOW()
            WHERE week_plan_id = :week_plan_id
            AND day_number = :day_number
        """),
        {"week_plan_id": week_plan_id, "day_number": day_number}
    )
    await db.commit()
    return {"message": f"Day {day_number} marked complete ✅"}


async def mark_week_complete(
    db: AsyncSession,
    week_plan_id: str
):
    """Mark entire week as completed."""
    await db.execute(
        text("""
            UPDATE week_plans
            SET is_completed = TRUE
            WHERE id = :week_plan_id
        """),
        {"week_plan_id": week_plan_id}
    )
    await db.commit()
    return {"message": "Week marked complete ✅"}


async def get_user_progress(
    db: AsyncSession,
    course_id: str,
    user_id: str
) -> dict:
    """Get full progress for a course."""

    # Total days
    total = await db.execute(
        text("""
            SELECT COUNT(*) as total
            FROM day_plans dp
            JOIN week_plans wp ON dp.week_plan_id = wp.id
            WHERE wp.course_id = :course_id
        """),
        {"course_id": course_id}
    )
    total_days = total.fetchone().total

    # Completed days
    completed = await db.execute(
        text("""
            SELECT COUNT(*) as completed
            FROM day_plans dp
            JOIN week_plans wp ON dp.week_plan_id = wp.id
            WHERE wp.course_id = :course_id
            AND dp.is_completed = TRUE
        """),
        {"course_id": course_id}
    )
    completed_days = completed.fetchone().completed

    # Quiz performance
    quiz_stats = await db.execute(
        text("""
            SELECT
                COUNT(*) as total_attempts,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
            FROM quiz_attempts
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    )
    quiz_row = quiz_stats.fetchone()

    # Knowledge state
    knowledge = await db.execute(
        text("""
            SELECT concept, confidence_score, times_practiced
            FROM user_knowledge_state
            WHERE user_id = :user_id
            ORDER BY confidence_score ASC
        """),
        {"user_id": user_id}
    )
    knowledge_rows = knowledge.fetchall()

    # Struggling concepts (confidence < 0.6)
    struggling = [
        {"concept": r.concept, "confidence": r.confidence_score}
        for r in knowledge_rows
        if r.confidence_score < 0.6
    ]

    # Strong concepts (confidence > 0.8)
    strong = [
        {"concept": r.concept, "confidence": r.confidence_score}
        for r in knowledge_rows
        if r.confidence_score >= 0.8
    ]

    completion_pct = round((completed_days / total_days * 100), 1) if total_days > 0 else 0
    quiz_score = round((quiz_row.correct / quiz_row.total_attempts * 100), 1) if quiz_row.total_attempts > 0 else 0

    return {
        "course_id": course_id,
        "completion_percentage": completion_pct,
        "days_completed": completed_days,
        "total_days": total_days,
        "quiz_score_percentage": quiz_score,
        "total_quiz_attempts": quiz_row.total_attempts,
        "struggling_concepts": struggling,
        "strong_concepts": strong
    }