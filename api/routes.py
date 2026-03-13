"""FastAPI route definitions for the RAG API."""

import logging

from fastapi import APIRouter, HTTPException

from api.models import (
    AskRequest,
    AskResponse,
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
