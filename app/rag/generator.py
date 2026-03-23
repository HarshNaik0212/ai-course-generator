from langchain_groq import ChatGroq
from app.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


# ── get_llm MUST be defined first ──────────────────────────
def get_llm(streaming: bool = False):
    return ChatGroq(
        api_key=settings.groq_api_key,
        model="llama-3.3-70b-versatile",
        temperature=0.7,
        streaming=streaming,
    )


# ── Retry wrapper (uses get_llm, so defined after) ─────────
async def llm_invoke_with_retry(
    prompt: str,
    max_retries: int = 3,
    delay_seconds: float = 2.0,
) -> str:
    llm = get_llm(streaming=False)
    last_error = None

    for attempt in range(max_retries):
        try:
            response = await llm.ainvoke(prompt)
            return response.content
        except Exception as e:
            last_error = e
            logger.warning(f"LLM call failed (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay_seconds)

    raise Exception(f"LLM failed after {max_retries} attempts: {last_error}")


# ── Prompt builder ──────────────────────────────────────────
def build_rag_prompt(
    question: str,
    context_chunks: list,
    conversation_history: list = [],
    knowledge_state: dict = {}          # ← ADD THIS PARAMETER
) -> str:
    # Format retrieved chunks
    context = "\n\n".join([
        f"[Source {i+1}: {c['title']}]\n{c['content']}"
        for i, c in enumerate(context_chunks)
    ])

    # Format past conversation
    history_text = ""
    if conversation_history:
        history_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in conversation_history[-6:]
        ])
        history_text = f"\nConversation so far:\n{history_text}\n"

    # Format knowledge state
    knowledge_text = ""
    if knowledge_state:
        struggling = [
            c for c, d in knowledge_state.items()
            if d.get("confidence", 1) < 0.6
        ]
        strong = [
            c for c, d in knowledge_state.items()
            if d.get("confidence", 0) >= 0.8
        ]
        if struggling:
            knowledge_text += f"\nUser struggles with: {', '.join(struggling)}"
            knowledge_text += " → explain these carefully with examples."
        if strong:
            knowledge_text += f"\nUser already knows: {', '.join(strong)}"
            knowledge_text += " → don't over-explain these."

    return f"""You are an expert coding tutor helping students learn programming.
Use the context below to answer the question. Be clear and concise.
If the context doesn't have the answer, use your own knowledge.
{knowledge_text}

CONTEXT:
{context}
{history_text}
STUDENT QUESTION: {question}

ANSWER:"""