"""FastAPI route definitions for the RAG API."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models import (
    AskRequest,
    AskResponse,
    DemosResponse,
    DocumentContentResponse,
    DocumentsResponse,
    HealthResponse,
)
from api.rag_service import DEFAULT_DEMO, CloudRAGService

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


# --- Demo-scoped endpoints ---


@router.get("/demos", response_model=DemosResponse)
async def list_demos() -> DemosResponse:
    """List all available demos.

    Returns:
        List of demo slugs and names.
    """
    service = get_rag_service()
    demos = service.get_demos()
    return DemosResponse(demos=demos)


@router.post("/demos/{demo}/ask", response_model=AskResponse)
async def ask_question_demo(demo: str, request: AskRequest) -> AskResponse:
    """Answer a question using the RAG pipeline for a specific demo.

    Args:
        demo: Demo slug.
        request: Question request body.

    Returns:
        Answer with sources and confidence.
    """
    service = get_rag_service()
    try:
        return service.ask(request.question, demo_slug=demo)
    except Exception:
        logger.exception("Error processing question for demo %s", demo)
        raise HTTPException(status_code=500, detail="Failed to process question")


@router.post("/demos/{demo}/ask/stream")
async def ask_question_stream_demo(demo: str, request: AskRequest) -> StreamingResponse:
    """Stream an answer using the RAG pipeline via SSE for a specific demo.

    Args:
        demo: Demo slug.
        request: Question request body.

    Returns:
        StreamingResponse with text/event-stream media type.
    """
    service = get_rag_service()
    return StreamingResponse(
        service.ask_stream(request.question, demo_slug=demo),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/demos/{demo}/documents", response_model=DocumentsResponse)
async def list_documents_demo(demo: str) -> DocumentsResponse:
    """List all indexed documents for a specific demo.

    Args:
        demo: Demo slug.

    Returns:
        List of document metadata.
    """
    service = get_rag_service()
    documents = service.list_documents(demo_slug=demo)
    return DocumentsResponse(documents=documents)


@router.get("/demos/{demo}/documents/{slug}", response_model=DocumentContentResponse)
async def get_document_demo(demo: str, slug: str) -> DocumentContentResponse:
    """Get full content for a single document within a demo.

    Args:
        demo: Demo slug.
        slug: Document slug (filename stem).

    Returns:
        Document content with metadata.

    Raises:
        HTTPException: 404 if document not found.
    """
    service = get_rag_service()
    result = service.get_document(slug, demo_slug=demo)
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


# --- Legacy endpoints (alias to default demo for backwards compat) ---


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest) -> AskResponse:
    """Answer a question using the RAG pipeline (default demo).

    Args:
        request: Question request body.

    Returns:
        Answer with sources and confidence.
    """
    return await ask_question_demo(DEFAULT_DEMO, request)


@router.post("/ask/stream")
async def ask_question_stream(request: AskRequest) -> StreamingResponse:
    """Stream an answer using the RAG pipeline via SSE (default demo).

    Args:
        request: Question request body.

    Returns:
        StreamingResponse with text/event-stream media type.
    """
    return await ask_question_stream_demo(DEFAULT_DEMO, request)


@router.get("/documents", response_model=DocumentsResponse)
async def list_documents() -> DocumentsResponse:
    """List all indexed documents (default demo).

    Returns:
        List of document metadata.
    """
    return await list_documents_demo(DEFAULT_DEMO)


@router.get("/documents/{slug}", response_model=DocumentContentResponse)
async def get_document(slug: str) -> DocumentContentResponse:
    """Get full content for a single document (default demo).

    Args:
        slug: Document slug (filename stem).

    Returns:
        Document content with metadata.

    Raises:
        HTTPException: 404 if document not found.
    """
    return await get_document_demo(DEFAULT_DEMO, slug)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check service health status.

    Returns:
        Health status including Pinecone connectivity.
    """
    service = get_rag_service()
    return service.health_check()
