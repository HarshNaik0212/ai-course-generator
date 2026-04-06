from app.rag.generator import llm_invoke_with_retry
from typing import List
import logging

logger = logging.getLogger(__name__)


async def prepend_context_to_chunk(
    chunk: str,
    document_title: str,
    document_summary: str = ""
) -> str:
    """
    Before embedding a chunk, prepend 2-3 sentences of context
    so the chunk makes sense when retrieved in isolation.
    (Anthropic's Contextual RAG — 49% fewer retrieval failures)
    """
    prompt = f"""Here is a document titled: "{document_title}"

Document overview: {document_summary[:500] if document_summary else "A technical document"}

Here is a specific chunk from this document:
<chunk>
{chunk}
</chunk>

In 2-3 sentences, explain what this chunk is about in the context 
of the full document. Be very concise. Do not repeat the chunk content.

CONTEXT:"""

    try:
        context = await llm_invoke_with_retry(prompt, max_retries=2)
        contextualized = f"{context.strip()}\n\n{chunk}"
        return contextualized
    except Exception as e:
        logger.warning(f"Contextual prepend failed, using raw chunk: {e}")
        return chunk  # fallback to raw chunk if LLM fails


async def contextualize_chunks_batch(
    chunks: List[str],
    document_title: str,
    document_summary: str = "",
    max_chunks: int = 50  # limit to avoid too many LLM calls
) -> List[str]:
    """
    Contextualize all chunks for a document.
    Limits to first max_chunks to control cost.
    """
    import asyncio

    # Only contextualize if document is not too large
    chunks_to_process = chunks[:max_chunks]
    logger.info(f"Contextualizing {len(chunks_to_process)} chunks for '{document_title}'")

    # Process sequentially to avoid overwhelming the LLM
    contextualized = []
    for i, chunk in enumerate(chunks_to_process):
        result = await prepend_context_to_chunk(
            chunk, document_title, document_summary
        )
        contextualized.append(result)
        if (i + 1) % 10 == 0:
            logger.info(f"Contextualized {i+1}/{len(chunks_to_process)} chunks")

    # For remaining chunks beyond max_chunks, use raw
    if len(chunks) > max_chunks:
        contextualized.extend(chunks[max_chunks:])

    return contextualized