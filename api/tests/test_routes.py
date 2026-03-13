"""Tests for FastAPI route handlers."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.models import (
    AskResponse,
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
