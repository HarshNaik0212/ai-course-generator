from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel, field_validator
from typing import List, Optional
from app.db.postgres import get_db
from app.agents.course_gen import course_graph
from app.memory.progress import mark_day_complete, mark_week_complete, get_user_progress
from app.adaptive.learning_engine import get_adaptive_recommendation
import uuid

router = APIRouter()

class GenerateCourseRequest(BaseModel):
    user_id: str
    topic: str
    skill_level: str            # beginner / intermediate / advanced
    hours_per_day: int          # 1, 2, 3, 4
    duration_weeks: int         # 2, 4, 8
    goals: List[str]            # ["get a job", "build projects"]

    @field_validator("skill_level")
    def validate_skill_level(cls, v):
        allowed = ["beginner", "intermediate", "advanced"]
        if v.lower() not in allowed:
            raise ValueError(f"skill_level must be one of: {allowed}")
        return v.lower()

    @field_validator("hours_per_day")
    def validate_hours(cls, v):
        if not 1 <= v <= 8:
            raise ValueError("hours_per_day must be between 1 and 8")
        return v

    @field_validator("duration_weeks")
    def validate_weeks(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("duration_weeks must be between 1 and 12")
        return v

    @field_validator("topic")
    def validate_topic(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("topic must be at least 3 characters")
        return v.strip()

    @field_validator("goals")
    def validate_goals(cls, v):
        if not v:
            raise ValueError("at least one goal is required")
        return v

class SubmitAnswerRequest(BaseModel):
    user_id: str
    question_id: str
    user_answer: str


@router.post("/generate")
async def generate_course(
    request: GenerateCourseRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a full personalized course plan:
    - Curriculum
    - Week by week plan
    - Day by day tasks
    - Quiz questions per week
    """
    # Convert user_id to valid UUID
    try:
        uuid.UUID(request.user_id)
        user_id = request.user_id
    except ValueError:
        user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, request.user_id))

    # Auto-create user if not exists
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

    try:
        # Run LangGraph course generation
        result = await course_graph.ainvoke({
            "user_id": user_id,
            "topic": request.topic,
            "skill_level": request.skill_level,
            "hours_per_day": request.hours_per_day,
            "duration_weeks": request.duration_weeks,
            "goals": request.goals,
            "course_id": "",
            "curriculum": {},
            "week_plans": [],
            "day_plans": [],
            "quiz_questions": [],
            "db": db,
            "error": None
        })

        return {
            "success": True,
            "course_id": result["course_id"],
            "course_title": result["curriculum"]["course_title"],
            "course_description": result["curriculum"]["course_description"],
            "duration_weeks": request.duration_weeks,
            "total_weeks": len(result["week_plans"]),
            "total_quiz_questions": len(result["quiz_questions"]),
            "week_plans": result["week_plans"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{course_id}")
async def get_course(
    course_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a course with all its week and day plans."""

    # Get course
    course = await db.execute(
        text("SELECT * FROM courses WHERE id = :id"),
        {"id": course_id}
    )
    course_row = course.fetchone()
    if not course_row:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get week plans
    weeks = await db.execute(
        text("""
            SELECT * FROM week_plans
            WHERE course_id = :course_id
            ORDER BY week_number
        """),
        {"course_id": course_id}
    )
    week_rows = weeks.fetchall()

    # Get day plans for each week
    full_plan = []
    for week in week_rows:
        days = await db.execute(
            text("""
                SELECT * FROM day_plans
                WHERE week_plan_id = :week_id
                ORDER BY day_number
            """),
            {"week_id": str(week.id)}
        )
        day_rows = days.fetchall()
        full_plan.append({
            "week_number": week.week_number,
            "theme": week.theme,
            "objectives": week.objectives,
            "days": [
                {
                    "day_number": d.day_number,
                    "tasks": d.tasks,
                    "is_completed": d.is_completed
                }
                for d in day_rows
            ]
        })

    return {
        "course_id": course_id,
        "topic": course_row.topic,
        "duration_weeks": course_row.duration_weeks,
        "status": course_row.status,
        "week_plans": full_plan
    }


@router.get("/{course_id}/quiz")
async def get_quiz(
    course_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all quiz questions for a course."""
    result = await db.execute(
        text("""
            SELECT * FROM quiz_questions
            WHERE course_id = :course_id
            ORDER BY difficulty
        """),
        {"course_id": course_id}
    )
    rows = result.fetchall()
    return {
        "course_id": course_id,
        "total_questions": len(rows),
        "questions": [
            {
                "id": str(r.id),
                "question_text": r.question_text,
                "question_type": r.question_type,
                "options": r.options,
                "difficulty": r.difficulty,
                "concept_tags": r.concept_tags
            }
            for r in rows
        ]
    }

@router.post("/quiz/submit")
async def submit_answer(
    request: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db)
):
    # Convert user_id
    try:
        uuid.UUID(request.user_id)
        user_id = request.user_id
    except ValueError:
        user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, request.user_id))

    # Fetch correct answer from DB
    result = await db.execute(
        text("""
            SELECT correct_answer, explanation, concept_tags
            FROM quiz_questions
            WHERE id = :id
        """),
        {"id": request.question_id}
    )
    question = result.fetchone()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check answer
    is_correct = request.user_answer.strip().upper() == \
                 question.correct_answer.strip().upper()

    # Save attempt to quiz_attempts table
    await db.execute(
        text("""
            INSERT INTO quiz_attempts
                (id, user_id, question_id, user_answer, is_correct)
            VALUES
                (:id, :user_id, :question_id, :user_answer, :is_correct)
        """),
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "question_id": request.question_id,
            "user_answer": request.user_answer,
            "is_correct": is_correct
        }
    )

    # Update user knowledge state (confidence score)
    for concept in (question.concept_tags or []):
        score_change = 0.1 if is_correct else -0.05
        await db.execute(
            text("""
                INSERT INTO user_knowledge_state
                    (id, user_id, concept, confidence_score, times_practiced)
                VALUES
                    (:id, :user_id, :concept, :score, 1)
                ON CONFLICT (user_id, concept)
                DO UPDATE SET
                    confidence_score = LEAST(1.0, GREATEST(0.0,
                        user_knowledge_state.confidence_score + :score)),
                    times_practiced = user_knowledge_state.times_practiced + 1,
                    updated_at = NOW()
            """),
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "concept": concept,
                "score": score_change
            }
        )

    await db.commit()

    return {
        "is_correct": is_correct,
        "your_answer": request.user_answer,
        "correct_answer": question.correct_answer if not is_correct else None,
        "explanation": question.explanation,
        "concept_tags": question.concept_tags
    }

@router.post("/{course_id}/day/{week_plan_id}/{day_number}/complete")
async def complete_day(
    course_id: str,
    week_plan_id: str,
    day_number: int,
    db: AsyncSession = Depends(get_db)
):
    """Mark a day as completed."""
    return await mark_day_complete(db, week_plan_id, day_number)


@router.post("/{course_id}/week/{week_plan_id}/complete")
async def complete_week(
    course_id: str,
    week_plan_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Mark a week as completed."""
    return await mark_week_complete(db, week_plan_id)


@router.get("/{course_id}/progress/{user_id}")
async def course_progress(
    course_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get full progress report for a user on a course."""
    try:
        uuid.UUID(user_id)
    except ValueError:
        user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_id))

    return await get_user_progress(db, course_id, user_id)


@router.get("/{course_id}/adaptive/{user_id}")
async def adaptive_recommendation(
    course_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get adaptive learning recommendations based on quiz performance."""
    try:
        uuid.UUID(user_id)
    except ValueError:
        user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_id))

    return await get_adaptive_recommendation(db, user_id, course_id)