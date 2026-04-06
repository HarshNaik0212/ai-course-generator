import httpx
import asyncio
import logging
from app.config import settings

logger = logging.getLogger(__name__)

LLM_URL = f"{settings.amd_llm_url}/v1/chat/completions"
MODEL_NAME = "qwen-coder"


def get_llm_url() -> str:
    return LLM_URL


async def call_llm(
    prompt: str,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    stream: bool = False
):
    """Call fine-tuned Qwen 7B on AMD MI300x."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            LLM_URL,
            json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": stream
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def llm_invoke_with_retry(
    prompt: str,
    max_retries: int = 3,
    delay_seconds: float = 2.0,
) -> str:
    """Call LLM with automatic retry on failure."""
    last_error = None

    for attempt in range(max_retries):
        try:
            return await call_llm(prompt)
        except Exception as e:
            last_error = e
            logger.warning(
                f"LLM call failed (attempt {attempt+1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(delay_seconds)

    raise Exception(f"LLM failed after {max_retries} attempts: {last_error}")


async def stream_llm(prompt: str):
    """
    Stream tokens from fine-tuned Qwen 7B.
    Yields one token at a time.
    """
    # Use high timeout for streaming (TTFT can be slow for remote LLM)
    timeout = httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=180.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            LLM_URL,
            json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
                "temperature": 0.7,
                "stream": True
            }
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta and delta["content"]:
                            yield delta["content"]
                    except Exception:
                        continue


def build_rag_prompt(
    question: str,
    context_chunks: list,
    conversation_history: list = [],
    knowledge_state: dict = {}
) -> str:
    # Format retrieved chunks
    context = "\n\n".join([
        f"[Source {i+1}: {c['title']}]\n{c['content']}"
        for i, c in enumerate(context_chunks)
    ])

    # Format conversation history
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