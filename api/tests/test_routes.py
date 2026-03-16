"""Tests for FastAPI route handlers."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.models import (
    AskResponse,
    DocumentContentResponse,
    DocumentInfo,
    DocumentsResponse,
    HealthResponse,
    SourceResponse,
)


class TestAskEndpoint:
    """Tests for POST /ask endpoint."""

    def test_ask_valid_question(
        self, test_client: TestClient, mock_rag_service: MagicMock
    ) -> None:
        """Test asking a valid question returns 200 with answer."""
        response = test_client.post(
            "/ask", json={"question": "What is the PTO policy?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "confidence" in data
        mock_rag_service.ask.assert_called_once_with("What is the PTO policy?")

    def test_ask_empty_question(self, test_client: TestClient) -> None:
        """Test that an empty question returns 422."""
        response = test_client.post("/ask", json={"question": ""})
        assert response.status_code == 422

    def test_ask_missing_question(self, test_client: TestClient) -> None:
        """Test that a missing question field returns 422."""
        response = test_client.post("/ask", json={})
        assert response.status_code == 422

    def test_ask_question_too_long(self, test_client: TestClient) -> None:
        """Test that a question exceeding max length returns 422."""
        response = test_client.post("/ask", json={"question": "x" * 1001})
        assert response.status_code == 422

    def test_ask_service_error(
        self, test_client: TestClient, mock_rag_service: MagicMock
    ) -> None:
        """Test that a service error returns 500."""
        mock_rag_service.ask.side_effect = Exception("Service error")

        response = test_client.post(
            "/ask", json={"question": "What is the PTO policy?"}
        )

        assert response.status_code == 500


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_check(
        self, test_client: TestClient, mock_rag_service: MagicMock
    ) -> None:
        """Test health check returns 200 with status."""
        mock_rag_service.health_check.return_value = HealthResponse(
            status="healthy",
            pinecone_connected=True,
            documents_indexed=5,
        )

        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["pinecone_connected"] is True


class TestDocumentsEndpoint:
    """Tests for GET /documents endpoint."""

    def test_list_documents(
        self, test_client: TestClient, mock_rag_service: MagicMock
    ) -> None:
        """Test listing documents returns 200 with document list."""
        mock_rag_service.list_documents.return_value = [
            DocumentInfo(name="Employee Handbook", document_type="hr", page_count=9),
            DocumentInfo(
                name="Engineering Runbook", document_type="engineering", page_count=7
            ),
        ]

        response = test_client.get("/documents")

        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 2
        assert data["documents"][0]["name"] == "Employee Handbook"


class TestGetDocumentEndpoint:
    """Tests for GET /documents/{slug} endpoint."""

    def test_get_document_success(
        self, test_client: TestClient, mock_rag_service: MagicMock
    ) -> None:
        """Test getting a document by slug returns 200."""
        response = test_client.get("/documents/employee-handbook")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Employee Handbook"
        assert data["slug"] == "employee-handbook"
        assert data["document_type"] == "hr"
        assert data["owner"] == "HR Team"
        assert "content" in data
        mock_rag_service.get_document.assert_called_once_with("employee-handbook")

    def test_get_document_not_found(
        self, test_client: TestClient, mock_rag_service: MagicMock
    ) -> None:
        """Test getting a nonexistent document returns 404."""
        mock_rag_service.get_document.return_value = None

        response = test_client.get("/documents/nonexistent")

        assert response.status_code == 404


class TestAskStreamEndpoint:
    """Tests for POST /ask/stream endpoint."""

    def test_ask_stream_returns_event_stream(
        self, test_client: TestClient, mock_rag_service: MagicMock
    ) -> None:
        """Test that /ask/stream returns text/event-stream content type."""

        async def fake_stream(question: str):
            yield 'event: sources\ndata: {"sources": [], "confidence": "high"}\n\n'
            yield "event: token\ndata: Hello\n\n"
            yield "event: done\ndata: [DONE]\n\n"

        mock_rag_service.ask_stream = fake_stream

        response = test_client.post(
            "/ask/stream", json={"question": "What is the PTO policy?"}
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        body = response.text
        assert "event: sources" in body
        assert "event: token" in body
        assert "event: done" in body

    def test_ask_stream_empty_question(self, test_client: TestClient) -> None:
        """Test that an empty question returns 422."""
        response = test_client.post("/ask/stream", json={"question": ""})
        assert response.status_code == 422


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_allows_localhost(self, test_client: TestClient) -> None:
        """Test that CORS allows localhost origins."""
        response = test_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
