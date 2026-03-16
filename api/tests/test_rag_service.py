"""Tests for the CloudRAGService."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AIMessageChunk

from api.config import CloudConfig
from api.rag_service import CloudRAGService, HIGH_CONFIDENCE_THRESHOLD


class TestCloudRAGServiceAsk:
    """Tests for CloudRAGService.ask method."""

    def _make_service(
        self,
        config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
    ) -> CloudRAGService:
        """Create a CloudRAGService with mocked dependencies."""
        with (
            patch("api.rag_service.GoogleGenerativeAIEmbeddings", return_value=mock_embeddings),
            patch("api.rag_service.PineconeVectorStore", return_value=mock_vectorstore),
            patch("api.rag_service.ChatGoogleGenerativeAI", return_value=mock_llm),
        ):
            return CloudRAGService(config)

    def test_ask_returns_answer_with_sources(
        self,
        cloud_config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
    ) -> None:
        """Test that ask returns an answer with source attributions."""
        service = self._make_service(
            cloud_config, mock_vectorstore, mock_llm, mock_embeddings
        )

        result = service.ask("What is the PTO policy?")

        assert result.answer
        assert len(result.sources) == 3
        assert result.sources[0].document_name == "Employee Handbook"
        assert result.sources[0].document_type == "hr"
        assert result.confidence == "high"

    def test_ask_empty_results_returns_low_confidence(
        self,
        cloud_config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
    ) -> None:
        """Test that empty search results return low confidence."""
        mock_vectorstore.similarity_search_with_score.return_value = []
        service = self._make_service(
            cloud_config, mock_vectorstore, mock_llm, mock_embeddings
        )

        result = service.ask("What is quantum physics?")

        assert result.confidence == "low"
        assert result.sources == []
        assert "don't have enough information" in result.answer

    def test_ask_low_scores_return_low_confidence(
        self,
        cloud_config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
    ) -> None:
        """Test that low similarity scores result in low confidence."""
        low_score_results = [
            (
                Document(
                    page_content="Some content",
                    metadata={
                        "source_document": "Test",
                        "document_type": "hr",
                        "section_number": 1,
                    },
                ),
                0.3,
            ),
        ]
        mock_vectorstore.similarity_search_with_score.return_value = low_score_results
        service = self._make_service(
            cloud_config, mock_vectorstore, mock_llm, mock_embeddings
        )

        result = service.ask("Something vague")

        assert result.confidence == "low"

    def test_ask_cross_document_sources(
        self,
        cloud_config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
        sample_search_results: list[tuple[Document, float]],
    ) -> None:
        """Test that sources from multiple documents are returned."""
        service = self._make_service(
            cloud_config, mock_vectorstore, mock_llm, mock_embeddings
        )

        result = service.ask("Tell me about company policies")

        document_names = {s.document_name for s in result.sources}
        assert len(document_names) > 1

    def test_ask_calls_llm_with_prompt(
        self,
        cloud_config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
    ) -> None:
        """Test that the LLM is invoked with a properly formatted prompt."""
        service = self._make_service(
            cloud_config, mock_vectorstore, mock_llm, mock_embeddings
        )

        service.ask("What is the PTO policy?")

        mock_llm.invoke.assert_called_once()
        messages = mock_llm.invoke.call_args[0][0]
        assert isinstance(messages, list)
        assert "What is the PTO policy?" in messages[1].content
        assert "Acme Corp" in messages[0].content


class TestCloudRAGServiceHealth:
    """Tests for CloudRAGService.health_check method."""

    def test_healthy_when_pinecone_connected(
        self,
        cloud_config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
    ) -> None:
        """Test health check returns healthy when Pinecone is connected."""
        with (
            patch("api.rag_service.GoogleGenerativeAIEmbeddings", return_value=mock_embeddings),
            patch("api.rag_service.PineconeVectorStore", return_value=mock_vectorstore),
            patch("api.rag_service.ChatGoogleGenerativeAI", return_value=mock_llm),
        ):
            service = CloudRAGService(cloud_config)

        result = service.health_check()

        assert result.status == "healthy"
        assert result.pinecone_connected is True

    def test_degraded_when_pinecone_fails(
        self,
        cloud_config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
    ) -> None:
        """Test health check returns degraded when Pinecone fails."""
        mock_vectorstore.similarity_search.side_effect = Exception("Connection failed")
        with (
            patch("api.rag_service.GoogleGenerativeAIEmbeddings", return_value=mock_embeddings),
            patch("api.rag_service.PineconeVectorStore", return_value=mock_vectorstore),
            patch("api.rag_service.ChatGoogleGenerativeAI", return_value=mock_llm),
        ):
            service = CloudRAGService(cloud_config)

        result = service.health_check()

        assert result.status == "degraded"
        assert result.pinecone_connected is False


class TestCloudRAGServiceGetDocument:
    """Tests for CloudRAGService.get_document method."""

    def test_get_document_returns_content(
        self,
        cloud_config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
    ) -> None:
        """Test get_document returns full document content."""
        with (
            patch("api.rag_service.GoogleGenerativeAIEmbeddings", return_value=mock_embeddings),
            patch("api.rag_service.PineconeVectorStore", return_value=mock_vectorstore),
            patch("api.rag_service.ChatGoogleGenerativeAI", return_value=mock_llm),
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            service = CloudRAGService(cloud_config)
            service.RESOURCES_DIR = tmpdir

            (Path(tmpdir) / "employee-handbook.md").write_text(
                "# Employee Handbook\n\n"
                "Last updated: January 15, 2025\n\n"
                "## 1. Welcome\n\nWelcome!\n"
            )

            result = service.get_document("employee-handbook")

        assert result is not None
        assert result.name == "Employee Handbook"
        assert result.slug == "employee-handbook"
        assert result.owner == "HR Team"
        assert result.section_count == 1

    def test_get_document_not_found(
        self,
        cloud_config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
    ) -> None:
        """Test get_document returns None for missing slug."""
        with (
            patch("api.rag_service.GoogleGenerativeAIEmbeddings", return_value=mock_embeddings),
            patch("api.rag_service.PineconeVectorStore", return_value=mock_vectorstore),
            patch("api.rag_service.ChatGoogleGenerativeAI", return_value=mock_llm),
            tempfile.TemporaryDirectory() as tmpdir,
        ):
            service = CloudRAGService(cloud_config)
            service.RESOURCES_DIR = tmpdir

            result = service.get_document("nonexistent")

        assert result is None


class TestCloudRAGServiceStream:
    """Tests for CloudRAGService.ask_stream method."""

    def _make_service(
        self,
        config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
    ) -> CloudRAGService:
        """Create a CloudRAGService with mocked dependencies."""
        with (
            patch("api.rag_service.GoogleGenerativeAIEmbeddings", return_value=mock_embeddings),
            patch("api.rag_service.PineconeVectorStore", return_value=mock_vectorstore),
            patch("api.rag_service.ChatGoogleGenerativeAI", return_value=mock_llm),
        ):
            return CloudRAGService(config)

    @pytest.mark.anyio
    async def test_ask_stream_yields_sources_tokens_done(
        self,
        cloud_config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
    ) -> None:
        """Test that ask_stream yields sources, then tokens, then done."""

        async def fake_astream(messages: list):
            yield AIMessageChunk(content="The ")
            yield AIMessageChunk(content="PTO policy")

        mock_llm.astream = fake_astream
        service = self._make_service(
            cloud_config, mock_vectorstore, mock_llm, mock_embeddings
        )

        events: list[str] = []
        async for event in service.ask_stream("What is the PTO policy?"):
            events.append(event)

        # First event: sources
        assert events[0].startswith("event: sources\n")
        sources_data = json.loads(events[0].split("data: ", 1)[1].strip())
        assert "sources" in sources_data
        assert sources_data["confidence"] == "high"
        assert len(sources_data["sources"]) == 3

        # Middle events: tokens (JSON-encoded to keep SSE data single-line)
        assert events[1] == 'event: token\ndata: "The "\n\n'
        assert events[2] == 'event: token\ndata: "PTO policy"\n\n'

        # Last event: done
        assert events[-1] == "event: done\ndata: [DONE]\n\n"

    @pytest.mark.anyio
    async def test_ask_stream_no_results(
        self,
        cloud_config: CloudConfig,
        mock_vectorstore: MagicMock,
        mock_llm: MagicMock,
        mock_embeddings: MagicMock,
    ) -> None:
        """Test that ask_stream handles no results gracefully."""
        mock_vectorstore.similarity_search_with_score.return_value = []
        service = self._make_service(
            cloud_config, mock_vectorstore, mock_llm, mock_embeddings
        )

        events: list[str] = []
        async for event in service.ask_stream("Unknown topic"):
            events.append(event)

        assert len(events) == 3
        sources_data = json.loads(events[0].split("data: ", 1)[1].strip())
        assert sources_data["sources"] == []
        assert sources_data["confidence"] == "low"
        assert "don't have enough information" in events[1]
        assert events[2] == "event: done\ndata: [DONE]\n\n"
