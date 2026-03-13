"""Cloud RAG service using Gemini + Pinecone."""

import logging

from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

from api.config import CloudConfig
from api.models import (
    AskResponse,
    DocumentInfo,
    HealthResponse,
    SourceResponse,
)
from api.prompts import build_prompt

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.3


class CloudRAGService:
    """RAG service backed by Gemini LLM and Pinecone vector store.

    Args:
        config: Cloud configuration with API keys and model settings.
    """

    def __init__(self, config: CloudConfig) -> None:
        self.config = config

        self.embeddings = HuggingFaceEmbeddings(
            model_name=config.embedding_model,
        )

        self.vectorstore = PineconeVectorStore(
            index_name=config.pinecone_index_name,
            embedding=self.embeddings,
            pinecone_api_key=config.pinecone_api_key,
        )

        self.llm = ChatGoogleGenerativeAI(
            model=config.llm_model,
            google_api_key=config.google_api_key,
            temperature=config.llm_temperature,
        )

        logger.info("CloudRAGService initialized with model=%s", config.llm_model)

    def ask(self, question: str) -> AskResponse:
        """Answer a question using RAG pipeline.

        Args:
            question: User's question.

        Returns:
            AskResponse with answer, sources, and confidence.
        """
        results: list[tuple[Document, float]] = (
            self.vectorstore.similarity_search_with_score(
                question, k=self.config.retrieval_k
            )
        )

        if not results:
            return AskResponse(
                answer="I don't have enough information in the available documents to answer that question.",
                sources=[],
                confidence="low",
            )

        chunks = [doc for doc, _ in results]
        scores = [score for _, score in results]

        avg_score = sum(scores) / len(scores)
        logger.info("Query: %s | Avg score: %.3f | Scores: %s", question, avg_score, [f"{s:.3f}" for s in scores])
        confidence = "high" if avg_score >= CONFIDENCE_THRESHOLD else "low"

        prompt = build_prompt(chunks, question)
        response = self.llm.invoke(prompt)
        answer = response.content

        sources = [
            SourceResponse(
                content=doc.page_content[:200],
                document_name=doc.metadata.get("source_document", "Unknown"),
                document_type=doc.metadata.get("document_type", "general"),
                section_number=doc.metadata.get("section_number", 0),
            )
            for doc in chunks
        ]

        return AskResponse(answer=answer, sources=sources, confidence=confidence)

    def list_documents(self) -> list[DocumentInfo]:
        """List all indexed documents with section counts.

        Returns:
            List of DocumentInfo objects.
        """
        # Query a broad search to gather metadata about indexed documents
        results: list[tuple[Document, float]] = (
            self.vectorstore.similarity_search_with_score(
                "document overview", k=100
            )
        )

        doc_sections: dict[str, set[int]] = {}
        doc_types: dict[str, str] = {}

        for doc, _ in results:
            name = doc.metadata.get("source_document", "Unknown")
            doc_type = doc.metadata.get("document_type", "general")
            section = doc.metadata.get("section_number", 0)

            if name not in doc_sections:
                doc_sections[name] = set()
                doc_types[name] = doc_type

            doc_sections[name].add(section)

        return [
            DocumentInfo(
                name=name,
                document_type=doc_types[name],
                page_count=len(sections),
            )
            for name, sections in sorted(doc_sections.items())
        ]

    def health_check(self) -> HealthResponse:
        """Check service health including Pinecone connectivity.

        Returns:
            HealthResponse with status information.
        """
        try:
            results = self.vectorstore.similarity_search("health check", k=1)
            pinecone_connected = True
            documents_indexed = len(results)
        except Exception:
            logger.exception("Pinecone health check failed")
            pinecone_connected = False
            documents_indexed = 0

        return HealthResponse(
            status="healthy" if pinecone_connected else "degraded",
            pinecone_connected=pinecone_connected,
            documents_indexed=documents_indexed,
        )
