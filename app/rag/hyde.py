from app.rag.generator import llm_invoke_with_retry
from app.rag.embedder import embedder
from typing import List
import logging
import asyncio

logger = logging.getLogger(__name__)


async def decompose_query(query: str) -> List[str]:
    """
    Break complex query into 3 simpler sub-questions.
    """
    prompt = f"""Break the following question into exactly 3 simpler sub-questions.
Return ONLY a JSON array of 3 strings. No explanation, no markdown.

QUESTION: {query}

JSON ARRAY:"""

    try:
        result = await llm_invoke_with_retry(prompt, max_retries=2)
        # Clean and parse
        result = result.strip()
        if "```" in result:
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()

        import json
        sub_questions = json.loads(result)

        # Validate it's a list of 3 strings
        if isinstance(sub_questions, list) and len(sub_questions) >= 2:
            logger.info(f"Decomposed into {len(sub_questions)} sub-questions")
            return sub_questions[:3]
    except Exception as e:
        logger.warning(f"Query decomposition failed: {e}, using original query")

    return [query]  # fallback to original


async def generate_hypothetical_answer(query: str) -> str:
    """
    HyDE: Generate a hypothetical ideal answer for the query.
    We then embed this answer and search for similar chunks.
    This improves recall on vague/paraphrased queries.
    """
    prompt = f"""Write a short, factual answer (3-5 sentences) to the following question.
Write as if you are an expert. Be specific and technical.
Do not say "I don't know" — always provide a substantive answer.

QUESTION: {query}

ANSWER:"""

    try:
        answer = await llm_invoke_with_retry(prompt, max_retries=2)
        logger.info(f"HyDE answer generated ({len(answer)} chars)")
        return answer.strip()
    except Exception as e:
        logger.warning(f"HyDE generation failed: {e}, using original query")
        return query  # fallback


async def get_hyde_embedding(query: str) -> List[float]:
    """Generate hypothetical answer and return its embedding."""
    hypothetical = await generate_hypothetical_answer(query)
    embedding = await embedder.aembed(hypothetical)
    return embedding