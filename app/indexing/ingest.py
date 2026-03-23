from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.rag.embedder import embedder
from app.indexing.chunker import chunk_text
from typing import Optional
import uuid
import json
import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from PDF bytes."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            full_text += f"\n[Page {page_num + 1}]\n{text}"
    doc.close()

    # Remove null bytes and non-UTF8 characters PostgreSQL can't handle
    full_text = full_text.replace("\x00", "")
    full_text = full_text.encode("utf-8", errors="ignore").decode("utf-8")

    print(f"Extracted {len(full_text)} characters from PDF")
    return full_text


async def ingest_pdf(
    db: AsyncSession,
    title: str,
    pdf_bytes: bytes,
    topic: str = "",
    metadata: Optional[dict] = None
) -> dict:
    """
    Full PDF ingestion pipeline:
    1. Extract text from PDF
    2. Save document record
    3. Chunk the text
    4. Embed each chunk
    5. Store in PostgreSQL with vectors
    """

    # Step 1 — Extract text from PDF
    content = extract_text_from_pdf(pdf_bytes)
    if not content.strip():
        raise ValueError("PDF appears to be empty or scanned (no extractable text)")

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

    # Step 3 — Chunk text
    chunks = chunk_text(content, chunk_size=500, overlap=50)
    print(f"PDF '{title}' → {len(chunks)} chunks")

    if not chunks:
        raise ValueError("No chunks created — PDF may have no readable text")

    # Step 4 — Embed all chunks in one batch
    embeddings = await embedder.aembed_batch(chunks)

    # Step 5 — Store chunks with embeddings
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = str(uuid.uuid4())
        embedding_str = "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"

        await db.execute(
            text("""
                INSERT INTO chunks
                    (id, document_id, content, chunk_index, level, dense_embedding)
                VALUES
                    (:id, :document_id, :content, :chunk_index, :level,
                     CAST(:embedding AS vector))
            """),
            {
                "id": chunk_id,
                "document_id": doc_id,
                "content": chunk,
                "chunk_index": i,
                "level": 0,
                "embedding": embedding_str
            }
        )

    await db.commit()

    return {
        "document_id": doc_id,
        "title": title,
        "topic": topic,
        "chunks_created": len(chunks),
        "pages_processed": content.count("[Page ")
    }