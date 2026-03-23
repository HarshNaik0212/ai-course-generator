from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from app.db.postgres import get_db
from app.indexing.ingest import ingest_pdf
from app.rag.retriever import hybrid_retrieve

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


@router.post("/ingest-pdf")
async def ingest_pdf_endpoint(
    file: UploadFile = File(..., description="PDF file to ingest"),
    title: str = Form(..., description="Title of the document"),
    topic: str = Form("", description="Topic/subject (e.g. python, machine learning)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload and ingest a PDF into the knowledge base.
    Extracts text → chunks → embeds → stores in PostgreSQL.
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    # Read PDF bytes
    pdf_bytes = await file.read()

    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    print(f"Received PDF: {file.filename} ({len(pdf_bytes)} bytes)")

    try:
        result = await ingest_pdf(
            db=db,
            title=title,
            pdf_bytes=pdf_bytes,
            topic=topic
        )
        return {"success": True, **result}

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Hybrid search over the knowledge base."""
    try:
        results = await hybrid_retrieve(
            db=db,
            query=request.query,
            top_k=request.top_k
        )
        return {
            "query": request.query,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))