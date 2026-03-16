"""Cloud RAG service using Gemini + Pinecone."""

import json
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from api.config import CloudConfig
from api.document_loader import (
    DOCUMENT_OWNERS,
    FILENAME_TO_TYPE,
    _filename_to_document_name,
    _is_stale,
    _parse_last_updated,
    load_full_document,
)
from api.models import (
    AskResponse,
    DocumentContentResponse,
    DocumentInfo,
    HealthResponse,
    SourceResponse,
)
from api.prompts import build_prompt

logger = logging.getLogger(__name__)

# Score thresholds calibrated for text-embedding-004 + Pinecone cosine
HIGH_CONFIDENCE_THRESHOLD = 0.45  # Top score above this → high confidence
RELEVANCE_CUTOFF = 0.30  # Chunks below this are excluded from context


class CloudRAGService:
    """RAG service backed by Gemini LLM and Pinecone vector store.

    Args:
        config: Cloud configuration with API keys and model settings.
    """

    RESOURCES_DIR = "resources/acme-corp"

    def __init__(self, config: CloudConfig) -> None:
        self.config = config

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=config.embedding_model,
            google_api_key=config.google_api_key,
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
            max_output_tokens=config.max_output_tokens,
            thinking_budget=0,
        )

        logger.info("CloudRAGService initialized with model=%s", config.llm_model)

    def _retrieve(
        self, question: str
    ) -> tuple[list[Document], list[SourceResponse], str] | None:
        """Retrieve relevant chunks, sources, and confidence for a question.

        Args:
            question: User's question.

        Returns:
            Tuple of (chunks, sources, confidence) or None if no relevant results.
        """
        results: list[tuple[Document, float]] = (
            self.vectorstore.similarity_search_with_score(
                question, k=self.config.retrieval_k
            )
        )

        if not results:
            return None

        scores = [score for _, score in results]
        top_score = max(scores)
        logger.info(
            "Query: %s | Top: %.3f | Scores: %s",
            question,
            top_score,
            [f"{s:.3f}" for s in scores],
        )

        relevant = [
            (doc, score) for doc, score in results if score >= RELEVANCE_CUTOFF
        ]

        if not relevant:
            return None

        chunks = [doc for doc, _ in relevant]
        confidence = "high" if top_score >= HIGH_CONFIDENCE_THRESHOLD else "low"

        sources = [
            SourceResponse(
                content=doc.page_content[:200],
                document_name=doc.metadata.get("source_document", "Unknown"),
                document_type=doc.metadata.get("document_type", "general"),
                section_number=doc.metadata.get("section_number", 0),
            )
            for doc in chunks
        ]

        return chunks, sources, confidence

    @staticmethod
    def _is_no_info_answer(answer: str) -> bool:
        """Check if the LLM's answer indicates it lacks sufficient information.

        Args:
            answer: The LLM-generated answer text.

        Returns:
            True if the answer is a "no information" response.
        """
        no_info_signals = [
            "i don't have enough information",
            "not covered in the available documents",
            "no information available",
            "documents do not contain",
            "documents don't contain",
            "not mentioned in",
            "cannot find",
            "no relevant information",
            "don't have enough information to compare",
            "do not provide information to compare",
            "don't have comparison data",
            "no comparison information",
            "not able to compare",
            "cannot compare",
            "don't have specific information",
            "no specific information",
            "isn't discussed in",
            "is not discussed in",
        ]
        lower = answer.lower()
        return any(signal in lower for signal in no_info_signals)

    def ask(self, question: str) -> AskResponse:
        """Answer a question using RAG pipeline.

        Args:
            question: User's question.

        Returns:
            AskResponse with answer, sources, and confidence.
        """
        no_info = "I don't have enough information in the available documents to answer that question."

        retrieval = self._retrieve(question)
        if retrieval is None:
            return AskResponse(answer=no_info, sources=[], confidence="low")

        chunks, sources, confidence = retrieval

        prompt = build_prompt(chunks, question)
        response = self.llm.invoke(prompt)
        answer = response.content

        # Override confidence when the LLM itself says it lacks information
        if self._is_no_info_answer(answer):
            confidence = "low"

        return AskResponse(
            answer=answer, sources=sources, confidence=confidence
        )

    async def ask_stream(self, question: str) -> AsyncGenerator[str, None]:
        """Stream an answer as SSE events.

        Yields sources immediately, then streams LLM tokens, then done.

        Args:
            question: User's question.

        Yields:
            SSE-formatted event strings.
        """
        no_info = "I don't have enough information in the available documents to answer that question."

        retrieval = self._retrieve(question)
        if retrieval is None:
            sources_data = json.dumps({"sources": [], "confidence": "low"})
            yield f"event: sources\ndata: {sources_data}\n\n"
            yield f"event: token\ndata: {json.dumps(no_info)}\n\n"
            yield "event: done\ndata: [DONE]\n\n"
            return

        chunks, sources, confidence = retrieval

        sources_data = json.dumps({
            "sources": [s.model_dump() for s in sources],
            "confidence": confidence,
        })
        yield f"event: sources\ndata: {sources_data}\n\n"

        prompt = build_prompt(chunks, question)
        full_answer: list[str] = []
        async for chunk in self.llm.astream(prompt):
            token = chunk.content
            if token:
                full_answer.append(token)
                yield f"event: token\ndata: {json.dumps(token)}\n\n"

        # Override confidence if the LLM declined to answer
        if self._is_no_info_answer("".join(full_answer)):
            override_data = json.dumps({"confidence": "low"})
            yield f"event: confidence_override\ndata: {override_data}\n\n"

        yield "event: done\ndata: [DONE]\n\n"

    def list_documents(self) -> list[DocumentInfo]:
        """List all indexed documents with section counts and freshness metadata.

        Returns:
            List of DocumentInfo objects.
        """
        results: list[tuple[Document, float]] = (
            self.vectorstore.similarity_search_with_score(
                "document overview", k=100
            )
        )

        doc_sections: dict[str, set[int]] = {}
        doc_types: dict[str, str] = {}
        doc_slugs: dict[str, str] = {}

        for doc, _ in results:
            name = doc.metadata.get("source_document", "Unknown")
            doc_type = doc.metadata.get("document_type", "general")
            section = doc.metadata.get("section_number", 0)
            source_file = doc.metadata.get("source_file", "")

            if name not in doc_sections:
                doc_sections[name] = set()
                doc_types[name] = doc_type
                slug = source_file.removesuffix(".md") if source_file else ""
                doc_slugs[name] = slug

            doc_sections[name].add(section)

        documents: list[DocumentInfo] = []
        for name in sorted(doc_sections):
            slug = doc_slugs[name]
            # Read freshness metadata from the markdown file
            last_updated: str | None = None
            is_stale = False
            owner = DOCUMENT_OWNERS.get(slug, "")

            md_path = Path(self.RESOURCES_DIR) / f"{slug}.md"
            if md_path.exists():
                content = md_path.read_text(encoding="utf-8")
                last_updated = _parse_last_updated(content)
                is_stale = _is_stale(last_updated)

            documents.append(
                DocumentInfo(
                    name=name,
                    document_type=doc_types[name],
                    page_count=len(doc_sections[name]),
                    slug=slug,
                    owner=owner,
                    last_updated=last_updated,
                    is_stale=is_stale,
                )
            )

        return documents

    def get_document(self, slug: str) -> DocumentContentResponse | None:
        """Get full content and metadata for a single document.

        Args:
            slug: Filename stem (e.g. 'employee-handbook').

        Returns:
            DocumentContentResponse or None if not found.
        """
        data = load_full_document(self.RESOURCES_DIR, slug)
        if data is None:
            return None
        return DocumentContentResponse(**data)

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
