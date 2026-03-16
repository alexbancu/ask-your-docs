"""Test fixtures and mocks for API tests."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.config import CloudConfig
from api.document_loader import ChunkDoc
from api.models import AskResponse, DemoInfo, DocumentContentResponse, SourceResponse


@pytest.fixture(params=["asyncio"])
def anyio_backend(request: pytest.FixtureRequest) -> str:
    """Restrict anyio tests to asyncio only (trio is not installed)."""
    return request.param


@pytest.fixture
def cloud_config() -> CloudConfig:
    """Create a test cloud configuration."""
    return CloudConfig(
        google_api_key="test-google-key",
        pinecone_api_key="test-pinecone-key",
        pinecone_index_name="test-index",
    )


@pytest.fixture
def sample_documents() -> list[ChunkDoc]:
    """Create sample documents with metadata."""
    return [
        ChunkDoc(
            page_content="All full-time employees receive 20 days of PTO per year.",
            metadata={
                "source_document": "Employee Handbook",
                "document_type": "hr",
                "section_number": 2,
                "source_file": "employee-handbook.md",
            },
        ),
        ChunkDoc(
            page_content="P1 incidents require 15-minute response time.",
            metadata={
                "source_document": "Engineering Runbook",
                "document_type": "engineering",
                "section_number": 1,
                "source_file": "engineering-runbook.md",
            },
        ),
        ChunkDoc(
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
def mock_pinecone_matches(sample_documents: list[ChunkDoc]) -> list[MagicMock]:
    """Create mock Pinecone query match objects."""
    matches = []
    scores = [0.85, 0.72, 0.65]
    for doc, score in zip(sample_documents, scores):
        match = MagicMock()
        match.score = score
        match.metadata = {**doc.metadata, "text": doc.page_content}
        matches.append(match)
    return matches


@pytest.fixture
def mock_index(mock_pinecone_matches: list[MagicMock]) -> MagicMock:
    """Create a mock Pinecone index."""
    mock = MagicMock()
    query_result = MagicMock()
    query_result.matches = mock_pinecone_matches
    mock.query.return_value = query_result
    return mock


@pytest.fixture
def mock_genai_client() -> MagicMock:
    """Create a mock google-genai client."""
    mock = MagicMock()

    # Mock embed_content
    embed_response = MagicMock()
    embedding = MagicMock()
    embedding.values = [0.1] * 3072
    embed_response.embeddings = [embedding]
    mock.models.embed_content.return_value = embed_response

    # Mock generate_content
    gen_response = MagicMock()
    gen_response.text = "Based on the Employee Handbook, all full-time employees receive 20 days of PTO per year."
    mock.models.generate_content.return_value = gen_response

    return mock


@pytest.fixture
def mock_rag_service(
    cloud_config: CloudConfig,
) -> MagicMock:
    """Create a mock CloudRAGService with pre-configured responses."""
    from api.rag_service import CloudRAGService

    service = MagicMock(spec=CloudRAGService)
    service.config = cloud_config

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

    service.get_document.return_value = DocumentContentResponse(
        name="Employee Handbook",
        slug="employee-handbook",
        document_type="hr",
        content="# Employee Handbook\n\nLast updated: January 15, 2025\n\n## 1. Welcome\n\nWelcome!",
        owner="HR Team",
        last_updated="January 15, 2025",
        is_stale=True,
        section_count=1,
    )

    service.get_demos.return_value = [
        DemoInfo(slug="acme-corp", name="Acme Corp"),
    ]

    return service


@pytest.fixture
def test_client(mock_rag_service: MagicMock) -> TestClient:
    """Create a FastAPI test client with mocked RAG service."""
    from api.app import create_app
    from api.routes import set_rag_service

    app = create_app()
    set_rag_service(mock_rag_service)

    return TestClient(app, raise_server_exceptions=False)
