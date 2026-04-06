from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.rag.embedder import embedder
from app.indexing.chunker import chunk_text
from app.indexing.raptor import build_raptor_levels
from app.indexing.contextual import contextualize_chunks_batch
from typing import Optional
import uuid
import json
import fitz
import logging
import re 


logger = logging.getLogger(__name__)



def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from PDF bytes with better layout handling and cleaning."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    
    for page_num, page in enumerate(doc):
        # Better extraction: use "text" mode + sort for reading order + dehyphenate
        text = page.get_text(
            "text",
            sort=True,                    # Helps with layout order
            flags=fitz.TEXT_DEHYPHENATE | fitz.TEXT_PRESERVE_LIGATURES
        )
        
        if text.strip():
            full_text += f"\n[Page {page_num + 1}]\n{text}"
    
    doc.close()

    # Final aggressive cleaning for repeated fragments (this fixes "lay lay lay", "ers ers ers", etc.)
    full_text = clean_repeated_fragments(full_text)

    # Clean null bytes and non-UTF8 chars
    full_text = full_text.replace("\x00", "")
    full_text = full_text.encode("utf-8", errors="ignore").decode("utf-8")

    logger.info(f"Extracted {len(full_text)} characters from PDF")
    return full_text


def clean_repeated_fragments(text: str) -> str:
    """Clean common PDF extraction artifacts like repeated words/fragments."""
    if not text:
        return text
    
    # 1. Re-join obvious hyphenated words that weren't caught by dehyphenate
    text = re.sub(r'(\w+)-\s*(\w+)', r'\1\2', text)
    
    # 2. Remove repeated words (e.g. "lay lay lay lay" → "lay")
    text = re.sub(r'\b(\w+)\s+\1(?:\s+\1){1,}', r'\1', text, flags=re.IGNORECASE)
    
    # 3. Remove repeated short fragments (e.g. "ers ers ers ers" → "ers")
    text = re.sub(r'(\b\w{2,6}\b)(?:\s+\1){3,}', r'\1', text, flags=re.IGNORECASE)
    
    # 4. Collapse any remaining excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


async def ingest_pdf(
    db: AsyncSession,
    title: str,
    pdf_bytes: bytes,
    topic: str = "",
    metadata: Optional[dict] = None,
    use_contextual_rag: bool = True,
    use_raptor: bool = True
) -> dict:
    """
    Full Phase 2 ingestion pipeline:
    1. Extract text from PDF
    2. Save document record
    3. Chunk the text
    4. Contextual RAG — prepend context to each chunk
    5. Embed contextualized chunks
    6. Store Level 0 chunks in PostgreSQL
    7. RAPTOR — build Level 1, 2 summaries
    """

    # Step 1 — Extract text
    content = extract_text_from_pdf(pdf_bytes)
    if not content.strip():
        raise ValueError("PDF appears to be empty or scanned")

    # Step 2 — Save document record
    doc_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO documents (id, title, doc_type, topic, metadata)
            VALUES (:id, :title, :doc_type, :topic, CAST(:metadata AS jsonb))
        """),
        {
            "id": doc_id,
            "title": title,
            "doc_type": "textbook",
            "topic": topic,
            "metadata": json.dumps(metadata or {})
        }
    )

    # Step 3 — Chunk
    raw_chunks = chunk_text(content, chunk_size=500, overlap=50)
    logger.info(f"PDF '{title}' → {len(raw_chunks)} raw chunks")

    if not raw_chunks:
        raise ValueError("No chunks created")

    # Step 4 — Contextual RAG (prepend context before embedding)
    if use_contextual_rag:
        logger.info("Applying Contextual RAG...")
        chunks_to_embed = await contextualize_chunks_batch(
            chunks=raw_chunks,  
            document_title=title,
            max_chunks=50
        )
    else:
        chunks_to_embed = raw_chunks

    # Step 5 — Embed all chunks
    logger.info("Embedding chunks...")
    embeddings = await embedder.aembed_batch(chunks_to_embed)

    # Step 6 — Store Level 0 chunks
    raw_chunk_ids = []
    for i, (raw_chunk, embedding) in enumerate(zip(raw_chunks, embeddings)):
        chunk_id = str(uuid.uuid4())
        raw_chunk_ids.append(chunk_id)
        embedding_str = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"

        await db.execute(
            text("""
                INSERT INTO chunks
                    (id, document_id, content, chunk_index,
                     level, dense_embedding, metadata)
                VALUES
                    (:id, :document_id, :content, :chunk_index,
                     :level, CAST(:embedding AS vector), CAST(:metadata AS jsonb))
            """),
            {
                "id": chunk_id,
                "document_id": doc_id,
                "content": raw_chunk,
                "chunk_index": i,
                "level": 0,
                "embedding": embedding_str,
                "metadata": json.dumps(metadata or {})
            }
        )

    await db.commit()
    logger.info(f"Stored {len(raw_chunks)} Level 0 chunks")

    # Step 7 — RAPTOR hierarchical indexing
    raptor_stats = {}
    if use_raptor and len(raw_chunks) >= 5:
        logger.info("Building RAPTOR hierarchy...")
        raptor_stats = await build_raptor_levels(
            db=db,
            document_id=doc_id,
            raw_chunks=raw_chunks,
            raw_chunk_ids=raw_chunk_ids
        )

    return {
        "document_id": doc_id,
        "title": title,
        "topic": topic,
        "level0_chunks": len(raw_chunks),
        "raptor": raptor_stats,
        "contextual_rag": use_contextual_rag,
        "pages_processed": content.count("[Page "),
        "level2_summary": raptor_stats.get("doc_summary_full", "")
    }