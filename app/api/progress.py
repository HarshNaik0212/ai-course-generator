from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.postgres import get_db
import uuid

router = APIRouter()


# ── Helper: convert user_id string to UUID ─────────────────
def resolve_user_id(user_id: str) -> str:
    try:
        uuid.UUID(user_id)
        return user_id
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, user_id))


# ── 1. Conversation history grouped by course ──────────────
@router.get("/chat/by-course/{course_id}")
async def get_chat_by_course(
    course_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get conversation history for a specific course.
    Used by sidebar to show course-wise chat folders.
    """
    uid = resolve_user_id(user_id)

    result = await db.execute(
        text("""
            SELECT DISTINCT ON (session_id)
                session_id,
                content as first_message,
                created_at
            FROM conversations
            WHERE user_id = :user_id
              AND course_id = :course_id
              AND role = 'user'
            ORDER BY session_id, created_at ASC
        """),
        {"user_id": uid, "course_id": course_id}
    )
    rows = result.fetchall()

    return {
        "course_id": course_id,
        "sessions": [
            {
                "session_id": str(r.session_id),
                "preview": r.first_message[:60] + "..." if len(r.first_message) > 60 else r.first_message,
                "created_at": str(r.created_at)
            }
            for r in rows
        ]
    }


# ── 2. Mark content as done → unlocks quiz ─────────────────
@router.post("/courses/{course_id}/day/{week_plan_id}/{day_number}/content-done")
async def mark_content_done(
    course_id: str,
    week_plan_id: str,
    day_number: int,
    db: AsyncSession = Depends(get_db)
):
    """
    User clicked 'Done' on study content.
    Unlocks the quiz for that day.
    """
    await db.execute(
        text("""
            UPDATE day_plans
            SET content_completed = TRUE
            WHERE week_plan_id = :week_plan_id
              AND day_number = :day_number
        """),
        {"week_plan_id": week_plan_id, "day_number": day_number}
    )
    await db.commit()

    return {
        "message": f"Content marked done for Day {day_number} ✅",
        "quiz_unlocked": True
    }


# ── 3. Get day lock/unlock status ──────────────────────────
@router.get("/courses/{course_id}/day/{week_plan_id}/{day_number}/status")
async def get_day_status(
    course_id: str,
    week_plan_id: str,
    day_number: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns lock status for a day.
    Day 1 always unlocked.
    Day N unlocked only if Day N-1 is completed.
    Quiz unlocked only if content_completed = TRUE.
    """
    # Get current day
    current = await db.execute(
        text("""
            SELECT is_completed, content_completed
            FROM day_plans
            WHERE week_plan_id = :week_plan_id
              AND day_number = :day_number
        """),
        {"week_plan_id": week_plan_id, "day_number": day_number}
    )
    current_row = current.fetchone()
    if not current_row:
        raise HTTPException(status_code=404, detail="Day not found")

    # Day 1 is always unlocked
    if day_number == 1:
        day_locked = False
    else:
        # Check if previous day is completed
        prev = await db.execute(
            text("""
                SELECT is_completed
                FROM day_plans
                WHERE week_plan_id = :week_plan_id
                  AND day_number = :prev_day
            """),
            {"week_plan_id": week_plan_id, "prev_day": day_number - 1}
        )
        prev_row = prev.fetchone()
        day_locked = not (prev_row and prev_row.is_completed)

    return {
        "day_number": day_number,
        "day_locked": day_locked,
        "content_completed": current_row.content_completed,
        "quiz_locked": not current_row.content_completed,
        "day_completed": current_row.is_completed
    }


# ── 4. Certificate status + auto-issue ─────────────────────
@router.get("/courses/{course_id}/certificate/{user_id}")
async def get_certificate(
    course_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Check certificate status.
    Auto-issues certificate if:
    - All days completed (100%)
    - Average quiz score > 50%
    """
    uid = resolve_user_id(user_id)

    # Check if already issued
    existing = await db.execute(
        text("""
            SELECT * FROM certificates
            WHERE user_id = :user_id AND course_id = :course_id
        """),
        {"user_id": uid, "course_id": course_id}
    )
    cert = existing.fetchone()
    if cert and cert.is_unlocked:
        return {
            "is_unlocked": True,
            "issued_at": str(cert.issued_at),
            "quiz_score_avg": cert.quiz_score_avg
        }

    # Check completion percentage
    total = await db.execute(
        text("""
            SELECT COUNT(*) as total FROM day_plans dp
            JOIN week_plans wp ON dp.week_plan_id = wp.id
            WHERE wp.course_id = :course_id
        """),
        {"course_id": course_id}
    )
    completed = await db.execute(
        text("""
            SELECT COUNT(*) as done FROM day_plans dp
            JOIN week_plans wp ON dp.week_plan_id = wp.id
            WHERE wp.course_id = :course_id
              AND dp.is_completed = TRUE
        """),
        {"course_id": course_id}
    )
    total_days = total.fetchone().total
    done_days = completed.fetchone().done
    completion_pct = (done_days / total_days * 100) if total_days > 0 else 0

    # Check average quiz score
    quiz_stats = await db.execute(
        text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct
            FROM quiz_attempts qa
            JOIN quiz_questions qq ON qa.question_id = qq.id
            WHERE qa.user_id = :user_id
              AND qq.course_id = :course_id
        """),
        {"user_id": uid, "course_id": course_id}
    )
    quiz_row = quiz_stats.fetchone()
    avg_score = (quiz_row.correct / quiz_row.total * 100) if quiz_row.total > 0 else 0

    # Issue certificate if eligible
    is_eligible = completion_pct >= 100 and avg_score >= 50

    if is_eligible:
        await db.execute(
            text("""
                INSERT INTO certificates
                    (id, user_id, course_id, quiz_score_avg, is_unlocked)
                VALUES
                    (:id, :user_id, :course_id, :score, TRUE)
                ON CONFLICT (user_id, course_id)
                DO UPDATE SET is_unlocked = TRUE, 
                              quiz_score_avg = :score,
                              issued_at = NOW()
            """),
            {
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "course_id": course_id,
                "score": avg_score
            }
        )
        await db.commit()

    return {
        "is_unlocked": is_eligible,
        "completion_percentage": round(completion_pct, 1),
        "quiz_score_avg": round(avg_score, 1),
        "message": "🎉 Certificate unlocked!" if is_eligible else
                   f"Complete all days (currently {round(completion_pct,1)}%) and score above 50% on quizzes to unlock certificate"
    }