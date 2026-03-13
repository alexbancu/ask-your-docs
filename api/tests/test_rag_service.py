"""Tests for the CloudRAGService."""

from unittest.mock import MagicMock, patch

from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from api.config import CloudConfig
from api.rag_service import CloudRAGService, CONFIDENCE_THRESHOLD


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
            patch("api.rag_service.HuggingFaceEmbeddings", return_value=mock_embeddings),
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
        prompt = mock_llm.invoke.call_args[0][0]
        assert "What is the PTO policy?" in prompt
        assert "Acme Corp" in prompt


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
            patch("api.rag_service.HuggingFaceEmbeddings", return_value=mock_embeddings),
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
            patch("api.rag_service.HuggingFaceEmbeddings", return_value=mock_embeddings),
            patch("api.rag_service.PineconeVectorStore", return_value=mock_vectorstore),
            patch("api.rag_service.ChatGoogleGenerativeAI", return_value=mock_llm),
        ):
            service = CloudRAGService(cloud_config)

        result = service.health_check()

        assert result.status == "degraded"
        assert result.pinecone_connected is False
