"""Pydantic request/response models for the RAG API."""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Request body for the /ask endpoint."""

    question: str = Field(..., min_length=1, max_length=1000)


class SourceResponse(BaseModel):
    """A single source chunk used to generate an answer."""

    content: str
    document_name: str
    document_type: str
    section_number: int


class AskResponse(BaseModel):
    """Response from the /ask endpoint."""

    answer: str
    sources: list[SourceResponse]
    confidence: str = Field(..., pattern="^(high|low)$")


class DocumentInfo(BaseModel):
    """Information about an indexed document."""

    name: str
    document_type: str
    page_count: int


class DocumentsResponse(BaseModel):
    """Response from the /documents endpoint."""

    documents: list[DocumentInfo]


class HealthResponse(BaseModel):
    """Response from the /health endpoint."""

    status: str
    pinecone_connected: bool
    documents_indexed: int
