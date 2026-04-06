import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.rag.embedder import embedder
from app.rag.generator import llm_invoke_with_retry
from typing import List, Dict
import uuid
import json
import logging

logger = logging.getLogger(__name__)


async def summarize_chunks(chunks: List[str]) -> str:
    """Summarize a group of chunks using Map-Reduce (no truncation)."""
    if not chunks:
        return ""

    if len(chunks) == 1:
        prompt = f"""Summarize the following text in 2-3 sentences only.
Be very concise. Key concepts only.
TEXT:
{chunks[0]}
SUMMARY:"""
        return await llm_invoke_with_retry(prompt, max_retries=2)

    # ── MAP: Summarize each chunk individually (parallel) ──
    map_prompts = [
        f"""Summarize the following text in 1-2 sentences only.
Be very concise. Extract only the key concepts.
TEXT:
{c}
SUMMARY:"""
        for c in chunks
    ]

    individual_summaries = await asyncio.gather(
        *[llm_invoke_with_retry(p, max_retries=2) for p in map_prompts],
        return_exceptions=True
    )

    valid_summaries = [
        s for s in individual_summaries
        if isinstance(s, str) and s.strip()
    ]

    if not valid_summaries:
        return "No valid summaries generated."

    # ── RECURSIVE COLLAPSE if too many summaries ──
    if len(valid_summaries) > 15:
        batches = [valid_summaries[i:i+10] for i in range(0, len(valid_summaries), 10)]
        collapsed = await asyncio.gather(
            *[summarize_chunks(batch) for batch in batches]
        )
        valid_summaries = [s for s in collapsed if isinstance(s, str) and s.strip()]

    # ── REDUCE: Merge individual summaries ──
    combined = "\n\n".join(valid_summaries)
    reduce_prompt = f"""Summarize the following key points into 2-3 sentences only.
Be very concise. Focus only on the most important concepts across all points.
KEY POINTS:
{combined}
SUMMARY:"""

    return await llm_invoke_with_retry(reduce_prompt, max_retries=2)


async def build_raptor_levels(
    db: AsyncSession,
    document_id: str,
    raw_chunks: List[str],
    raw_chunk_ids: List[str]    
) -> Dict:
    """
    Build 4-level RAPTOR hierarchy:
    Level 0 → raw chunks (already stored)
    Level 1 → section summaries (groups of 5 chunks)
    Level 2 → document summary (summary of all level 1)
    Level 3 → stored as document metadata
    """
    logger.info(f"Building RAPTOR for doc {document_id} with {len(raw_chunks)} chunks")

    level1_ids = []
    level1_summaries = []

    # ── Level 1: Section summaries (every 5 raw chunks) ──
    group_size = 5
    for i in range(0, len(raw_chunks), group_size):
        group = raw_chunks[i:i + group_size]
        group_ids = raw_chunk_ids[i:i + group_size]

        summary = await summarize_chunks(group)
        embedding = await embedder.aembed(summary)
        embedding_str = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"

        chunk_id = str(uuid.uuid4())
        # Use first chunk of group as parent reference
        parent_id = group_ids[0] if group_ids else None

        await db.execute(
            text("""
                INSERT INTO chunks
                    (id, document_id, content, chunk_index, level,
                     parent_chunk_id, dense_embedding)
                VALUES
                    (:id, :document_id, :content, :chunk_index, :level,
                     :parent_id, CAST(:embedding AS vector))
            """),
            {
                "id": chunk_id,
                "document_id": document_id,
                "content": summary,
                "chunk_index": i // group_size,
                "level": 1,
                "parent_id": parent_id,
                "embedding": embedding_str
            }
        )
        level1_ids.append(chunk_id)
        level1_summaries.append(summary)
        logger.info(f"Level 1 chunk {i//group_size + 1} created")

    # ── Level 2.0: Intermediate summaries (groups of 8 L1 summaries) ──
    L2_GROUP_SIZE = 8
    intermediate_summaries = []
    l2_batches = [level1_summaries[i:i + L2_GROUP_SIZE] for i in range(0, len(level1_summaries), L2_GROUP_SIZE)]
    logger.info(f"Level 2.0: {len(level1_summaries)} L1 summaries → {len(l2_batches)} intermediate groups")
 
    for batch in l2_batches:
        inter_summary = await summarize_chunks(batch)
        intermediate_summaries.append(inter_summary)
 
    # ── Level 2.5: Final document summary (merge all intermediates) ──
    doc_summary = await summarize_chunks(intermediate_summaries)
    logger.info(f"Level 2.5: merged {len(intermediate_summaries)} intermediates → final doc summary")
 
    embedding = await embedder.aembed(doc_summary)
    embedding_str = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"
 
    doc_summary_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO chunks
                (id, document_id, content, chunk_index, level,
                 parent_chunk_id, dense_embedding)
            VALUES
                (:id, :document_id, :content, :chunk_index, :level,
                 :parent_id, CAST(:embedding AS vector))
        """),
        {
            "id": doc_summary_id,
            "document_id": document_id,
            "content": doc_summary,
            "chunk_index": 0,
            "level": 2,
            "parent_id": level1_ids[0] if level1_ids else None,
            "embedding": embedding_str
        }
    )
    logger.info(f"Level 2 document summary created")
 
    await db.commit()
 
    return {
        "level0_chunks": len(raw_chunks),
        "level1_sections": len(level1_ids),
        "level2_doc_summary": 1,
        "doc_summary_preview": doc_summary[:200],
        "doc_summary_full": doc_summary
    }

async def build_level3_course_summary(
    db: AsyncSession,
    topic: str,
    level2_summaries: List[str],
    document_ids: List[str]
) -> str:
    """
    Level 3: Course-level summary across ALL documents in a subject.
    Called after all PDFs in a subject folder are ingested.
    Stored as a special level=3 chunk linked to first document.
    """
    if not level2_summaries:
        return ""

    logger.info(f"Building Level 3 course summary for topic: {topic}")

    # Use Map-Reduce on all Level 2 summaries
    course_summary = await summarize_chunks(level2_summaries)

    # Embed it
    embedding = await embedder.aembed(course_summary)
    embedding_str = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"

    # Store as level=3 chunk linked to first document
    chunk_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO chunks
                (id, document_id, content, chunk_index, level,
                 parent_chunk_id, dense_embedding, metadata)
            VALUES
                (:id, :document_id, :content, :chunk_index, :level,
                 NULL, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
        """),
        {
            "id": chunk_id,
            "document_id": document_ids[0],
            "content": course_summary,
            "chunk_index": 0,
            "level": 3,
            "embedding": embedding_str,
            "metadata": json.dumps({
                "topic": topic,
                "type": "course_summary",
                "covers_documents": len(document_ids)
            })
        }
    )
    await db.commit()
    logger.info(f"Level 3 course summary created for '{topic}'")
    return course_summary