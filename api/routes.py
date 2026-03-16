"""FastAPI route definitions for the RAG API."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models import (
    AskRequest,
    AskResponse,
    DocumentContentResponse,
    DocumentsResponse,
    HealthResponse,
)
from api.rag_service import CloudRAGService

logger = logging.getLogger(__name__)

router = APIRouter()

# Injected at app startup
_rag_service: CloudRAGService | None = None


def set_rag_service(service: CloudRAGService) -> None:
    """Set the RAG service instance for route handlers.

    Args:
        service: Initialized CloudRAGService.
    """
    global _rag_service
    _rag_service = service


def get_rag_service() -> CloudRAGService:
    """Get the RAG service instance.

    Returns:
        The active CloudRAGService.

    Raises:
        HTTPException: If service is not initialized.
    """
    if _rag_service is None:
        raise HTTPException(status_code=503, detail="RAG service not initialized")
    return _rag_service


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest) -> AskResponse:
    """Answer a question using the RAG pipeline.

    Args:
        request: Question request body.

    Returns:
        Answer with sources and confidence.
    """
    service = get_rag_service()
    try:
        return service.ask(request.question)
    except Exception:
        logger.exception("Error processing question")
        raise HTTPException(status_code=500, detail="Failed to process question")


@router.post("/ask/stream")
async def ask_question_stream(request: AskRequest) -> StreamingResponse:
    """Stream an answer using the RAG pipeline via SSE.

    Args:
        request: Question request body.

    Returns:
        StreamingResponse with text/event-stream media type.
    """
    service = get_rag_service()
    return StreamingResponse(
        service.ask_stream(request.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check service health status.

    Returns:
        Health status including Pinecone connectivity.
    """
    service = get_rag_service()
    return service.health_check()


@router.get("/documents", response_model=DocumentsResponse)
async def list_documents() -> DocumentsResponse:
    """List all indexed documents.

    Returns:
        List of document metadata.
    """
    service = get_rag_service()
    documents = service.list_documents()
    return DocumentsResponse(documents=documents)


@router.get("/documents/{slug}", response_model=DocumentContentResponse)
async def get_document(slug: str) -> DocumentContentResponse:
    """Get full content for a single document.

    Args:
        slug: Document slug (filename stem).

    Returns:
        Document content with metadata.

    Raises:
        HTTPException: 404 if document not found.
    """
    service = get_rag_service()
    result = service.get_document(slug)
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result
