from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import TypedDict, List, Optional
from app.rag.generator import llm_invoke_with_retry   # ← CHANGED
import uuid
import json
import logging

logger = logging.getLogger(__name__)

# ── State ──────────────────────────────────────────────────
class CourseState(TypedDict):
    user_id: str
    topic: str
    skill_level: str
    hours_per_day: int
    duration_weeks: int
    goals: List[str]
    course_id: str
    curriculum: dict
    week_plans: List[dict]
    day_plans: List[dict]
    quiz_questions: List[dict]
    db: object
    error: Optional[str]


# ── Safe JSON parser ────────────────────────────────────────
def safe_json_parse(content: str, fallback={}):
    try:
        if "```" in content:
            parts = content.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:]
                part = part.strip()
                if part.startswith("{") or part.startswith("["):
                    content = part
                    break
        content = content.strip()
        if not (content.startswith("{") or content.startswith("[")):
            start = content.find("{") if "{" in content else content.find("[")
            if start != -1:
                content = content[start:]
        return json.loads(content)
    except Exception as e:
        logger.warning(f"JSON parse failed: {e}\nContent: {content[:200]}")
        return fallback


# ── Node 1: Create course record ────────────────────────────
async def create_course_node(state: CourseState) -> dict:
    course_id = str(uuid.uuid4())
    db = state["db"]

    await db.execute(
        text("""
            INSERT INTO courses (id, user_id, topic, duration_weeks, hours_per_day, goals)
            VALUES (:id, :user_id, :topic, :duration_weeks, :hours_per_day, :goals)
        """),
        {
            "id": course_id,
            "user_id": state["user_id"],
            "topic": state["topic"],
            "duration_weeks": state["duration_weeks"],
            "hours_per_day": state["hours_per_day"],
            "goals": state["goals"]
        }
    )
    await db.commit()
    return {"course_id": course_id}


# ── Node 2: Generate curriculum ─────────────────────────────
async def generate_curriculum_node(state: CourseState) -> dict:
    prompt = f"""You are an expert course designer.
Create a structured curriculum for the following course.

Topic: {state["topic"]}
Skill Level: {state["skill_level"]}
Duration: {state["duration_weeks"]} weeks
Hours per day: {state["hours_per_day"]} hours
Goals: {", ".join(state["goals"])}

Return ONLY a JSON object like this (no extra text, no markdown):
{{
  "course_title": "...",
  "course_description": "...",
  "prerequisites": ["...", "..."],
  "weekly_themes": [
    {{"week": 1, "theme": "...", "objectives": ["...", "...", "..."]}},
    {{"week": 2, "theme": "...", "objectives": ["...", "...", "..."]}}
  ]
}}"""

    # ← CHANGED: using retry wrapper instead of llm.ainvoke
    content = await llm_invoke_with_retry(prompt)
    content = content.strip()

    curriculum = safe_json_parse(content)
    if not curriculum:
        raise Exception("Failed to generate curriculum — invalid JSON")

    return {"curriculum": curriculum}


# ── Node 3: Generate week plans ─────────────────────────────
async def generate_week_plans_node(state: CourseState) -> dict:
    db = state["db"]
    week_plans = []

    for week_data in state["curriculum"]["weekly_themes"]:
        prompt = f"""You are an expert course designer.
Create a detailed week plan for Week {week_data["week"]}.

Course Topic: {state["topic"]}
Week Theme: {week_data["theme"]}
Week Objectives: {", ".join(week_data["objectives"])}
Hours per day: {state["hours_per_day"]} hours
Skill Level: {state["skill_level"]}

Return ONLY a JSON object (no extra text, no markdown):
{{
  "week_number": {week_data["week"]},
  "theme": "{week_data["theme"]}",
  "objectives": {json.dumps(week_data["objectives"])},
  "days": [
    {{
      "day": 1,
      "title": "...",
      "tasks": [
        {{"type": "read", "title": "...", "duration_mins": 30}},
        {{"type": "practice", "title": "...", "duration_mins": 45}},
        {{"type": "project", "title": "...", "duration_mins": 30}}
      ]
    }}
  ]
}}"""

        # ← CHANGED
        content = await llm_invoke_with_retry(prompt)
        content = content.strip()

        week_plan = safe_json_parse(content)
        if not week_plan:
            raise Exception(f"Failed to generate week {week_data['week']} plan")

        # Save week plan to DB
        week_id = str(uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO week_plans
                    (id, course_id, week_number, theme, objectives)
                VALUES
                    (:id, :course_id, :week_number, :theme, :objectives)
            """),
            {
                "id": week_id,
                "course_id": state["course_id"],
                "week_number": week_plan["week_number"],
                "theme": week_plan["theme"],
                "objectives": week_plan["objectives"]
            }
        )

        # Save day plans to DB
        for day in week_plan.get("days", []):
            day_id = str(uuid.uuid4())
            await db.execute(
                text("""
                    INSERT INTO day_plans
                        (id, week_plan_id, day_number, tasks)
                    VALUES
                        (:id, :week_plan_id, :day_number, CAST(:tasks AS jsonb))
                """),
                {
                    "id": day_id,
                    "week_plan_id": week_id,
                    "day_number": day["day"],
                    "tasks": json.dumps(day.get("tasks", []))
                }
            )

        week_plan["week_id"] = week_id
        week_plans.append(week_plan)

    await db.commit()
    return {"week_plans": week_plans}


# ── Node 4: Generate quiz questions ─────────────────────────
async def generate_quiz_node(state: CourseState) -> dict:
    db = state["db"]
    all_questions = []

    for week in state["week_plans"]:
        prompt = f"""You are an expert quiz designer.
Create 3 quiz questions for this week's content.

Week Theme: {week["theme"]}
Objectives: {", ".join(week["objectives"])}
Skill Level: {state["skill_level"]}

Return ONLY a JSON array (no extra text, no markdown):
[
  {{
    "question_text": "...",
    "question_type": "mcq",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct_answer": "A",
    "explanation": "...",
    "difficulty": 2,
    "concept_tags": ["...", "..."]
  }},
  {{
    "question_text": "Write a function that...",
    "question_type": "code",
    "options": null,
    "correct_answer": "def solution(): ...",
    "explanation": "...",
    "difficulty": 3,
    "concept_tags": ["...", "..."]
  }}
]"""

        # ← CHANGED
        content = await llm_invoke_with_retry(prompt)
        content = content.strip()

        questions = safe_json_parse(content, fallback=[])
        if not questions:
            raise Exception(f"Failed to generate quiz for week {week['theme']}")

        for q in questions:
            q_id = str(uuid.uuid4())
            await db.execute(
                text("""
                    INSERT INTO quiz_questions
                        (id, course_id, question_text, question_type,
                         options, correct_answer, explanation,
                         difficulty, concept_tags)
                    VALUES
                        (:id, :course_id, :question_text, :question_type,
                         CAST(:options AS jsonb), :correct_answer,
                         :explanation, :difficulty, :concept_tags)
                """),
                {
                    "id": q_id,
                    "course_id": state["course_id"],
                    "question_text": q["question_text"],
                    "question_type": q["question_type"],
                    "options": json.dumps(q.get("options")),
                    "correct_answer": q["correct_answer"],
                    "explanation": q["explanation"],
                    "difficulty": q["difficulty"],
                    "concept_tags": q["concept_tags"]
                }
            )
            all_questions.append(q)

    await db.commit()
    return {"quiz_questions": all_questions}


# ── Build Graph ─────────────────────────────────────────────
def build_course_graph():
    graph = StateGraph(CourseState)

    graph.add_node("create_course",  create_course_node)
    graph.add_node("gen_curriculum", generate_curriculum_node)
    graph.add_node("gen_week_plans", generate_week_plans_node)
    graph.add_node("gen_quiz",       generate_quiz_node)

    graph.set_entry_point("create_course")
    graph.add_edge("create_course",  "gen_curriculum")
    graph.add_edge("gen_curriculum", "gen_week_plans")
    graph.add_edge("gen_week_plans", "gen_quiz")
    graph.add_edge("gen_quiz",       END)

    return graph.compile()

course_graph = build_course_graph()