"""Test fixtures and mocks for API tests."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from api.config import CloudConfig
from api.models import AskResponse, SourceResponse


@pytest.fixture
def cloud_config() -> CloudConfig:
    """Create a test cloud configuration."""
    return CloudConfig(
        google_api_key="test-google-key",
        pinecone_api_key="test-pinecone-key",
        pinecone_index_name="test-index",
    )


@pytest.fixture
def sample_documents() -> list[Document]:
    """Create sample documents with metadata."""
    return [
        Document(
            page_content="All full-time employees receive 20 days of PTO per year.",
            metadata={
                "source_document": "Employee Handbook",
                "document_type": "hr",
                "section_number": 2,
                "source_file": "employee-handbook.md",
            },
        ),
        Document(
            page_content="P1 incidents require 15-minute response time.",
            metadata={
                "source_document": "Engineering Runbook",
                "document_type": "engineering",
                "section_number": 1,
                "source_file": "engineering-runbook.md",
            },
        ),
        Document(
            page_content="All data is encrypted using AES-256 encryption.",
            metadata={
                "source_document": "Security Policy",
                "document_type": "security",
                "section_number": 1,
                "source_file": "security-policy.md",
            },
        ),
    ]


@pytest.fixture
def sample_search_results(
    sample_documents: list[Document],
) -> list[tuple[Document, float]]:
    """Create sample search results with scores."""
    return [
        (sample_documents[0], 0.85),
        (sample_documents[1], 0.72),
        (sample_documents[2], 0.65),
    ]


@pytest.fixture
def mock_vectorstore(
    sample_search_results: list[tuple[Document, float]],
) -> MagicMock:
    """Create a mock Pinecone vector store."""
    mock = MagicMock()
    mock.similarity_search_with_score.return_value = sample_search_results
    mock.similarity_search.return_value = [doc for doc, _ in sample_search_results]
    return mock


@pytest.fixture
def mock_llm() -> MagicMock:
    """Create a mock Gemini LLM that returns AIMessage."""
    mock = MagicMock()
    mock.invoke.return_value = AIMessage(
        content="Based on the Employee Handbook, all full-time employees receive 20 days of PTO per year."
    )
    return mock


@pytest.fixture
def mock_embeddings() -> MagicMock:
    """Create a mock embedding model."""
    mock = MagicMock()
    mock.embed_query.return_value = [0.1] * 384
    mock.embed_documents.return_value = [[0.1] * 384]
    return mock


@pytest.fixture
def mock_rag_service(
    cloud_config: CloudConfig,
    mock_vectorstore: MagicMock,
    mock_llm: MagicMock,
    mock_embeddings: MagicMock,
) -> MagicMock:
    """Create a mock CloudRAGService with pre-configured responses."""
    from api.rag_service import CloudRAGService

    service = MagicMock(spec=CloudRAGService)
    service.config = cloud_config
    service.vectorstore = mock_vectorstore
    service.llm = mock_llm
    service.embeddings = mock_embeddings

    service.ask.return_value = AskResponse(
        answer="All full-time employees receive 20 days of PTO per year.",
        sources=[
            SourceResponse(
                content="All full-time employees receive 20 days of PTO per year.",
                document_name="Employee Handbook",
                document_type="hr",
                section_number=2,
            )
        ],
        confidence="high",
    )

    return service


@pytest.fixture
def test_client(mock_rag_service: MagicMock) -> TestClient:
    """Create a FastAPI test client with mocked RAG service."""
    from api.app import create_app
    from api.routes import set_rag_service

    app = create_app()
    set_rag_service(mock_rag_service)

    return TestClient(app, raise_server_exceptions=False)
