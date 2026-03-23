from fastapi import FastAPI, Request, logger
from fastapi.responses import JSONResponse
from app.api.health import router as health_router
from app.api.documents import router as docs_router
from app.api.chat import router as chat_router
from app.api.courses import router as courses_router
from app.api.progress import router as progress_router
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s  - %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Course Generator", version="1.0.0")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )

app.include_router(health_router, prefix="/api")
app.include_router(docs_router, prefix="/api/docs")
app.include_router(chat_router,   prefix="/api")
app.include_router(courses_router, prefix="/api/courses")
app.include_router(progress_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "AI Course Generator API",
        "version": "1.0.0",
        "docs": "/docs"}    
    # return FileResponse("static/index.html")
