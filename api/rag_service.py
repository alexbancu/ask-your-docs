"""Cloud RAG service using Gemini + Pinecone (direct SDKs, no LangChain)."""

import json
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

from google import genai
from google.genai import types
from pinecone import Pinecone

from api.config import CloudConfig
from api.document_loader import (
    ChunkDoc,
    DemoConfig,
    _is_stale,
    _parse_last_updated,
    list_demos,
    load_demo_config,
    load_full_document,
)
from api.models import (
    AskResponse,
    DemoInfo,
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

DEFAULT_DEMO = "acme-corp"


class CloudRAGService:
    """RAG service backed by Gemini LLM and Pinecone vector store.

    Args:
        config: Cloud configuration with API keys and model settings.
    """

    def __init__(self, config: CloudConfig) -> None:
        self.config = config

        self.genai_client = genai.Client(api_key=config.google_api_key)

        pc = Pinecone(api_key=config.pinecone_api_key)
        self.index = pc.Index(config.pinecone_index_name)

        logger.info("CloudRAGService initialized with model=%s", config.llm_model)

    @staticmethod
    def _resources_dir(demo_slug: str) -> str:
        """Return the resources directory path for a demo.

        Args:
            demo_slug: Demo identifier.

        Returns:
            Path string like 'resources/acme-corp'.
        """
        return f"resources/{demo_slug}"

    @staticmethod
    def _demo_config(demo_slug: str) -> DemoConfig | None:
        """Load demo config, returning None if not found.

        Args:
            demo_slug: Demo identifier.

        Returns:
            DemoConfig or None.
        """
        try:
            return load_demo_config(demo_slug)
        except FileNotFoundError:
            return None

    def _embed_query(self, text: str) -> list[float]:
        """Embed a single query string.

        Args:
            text: The query text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        result = self.genai_client.models.embed_content(
            model=self.config.embedding_model,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return result.embeddings[0].values

    def _retrieve(
        self, question: str, demo_slug: str = DEFAULT_DEMO
    ) -> tuple[list[ChunkDoc], list[SourceResponse], str] | None:
        """Retrieve relevant chunks, sources, and confidence for a question.

        Args:
            question: User's question.
            demo_slug: Demo namespace for Pinecone query.

        Returns:
            Tuple of (chunks, sources, confidence) or None if no relevant results.
        """
        query_vector = self._embed_query(question)

        results = self.index.query(
            vector=query_vector,
            top_k=self.config.retrieval_k,
            include_metadata=True,
            namespace=demo_slug,
        )

        if not results.matches:
            return None

        scores = [match.score for match in results.matches]
        top_score = max(scores)
        logger.info(
            "Query: %s | Top: %.3f | Scores: %s",
            question,
            top_score,
            [f"{s:.3f}" for s in scores],
        )

        relevant = [
            (match, match.score)
            for match in results.matches
            if match.score >= RELEVANCE_CUTOFF
        ]

        if not relevant:
            return None

        chunks: list[ChunkDoc] = []
        for match, _ in relevant:
            metadata = dict(match.metadata) if match.metadata else {}
            page_content = metadata.pop("text", "")
            chunks.append(ChunkDoc(page_content=page_content, metadata=metadata))

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

    def _generate(self, prompt: dict[str, str]) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: Dict with 'system' and 'user' keys.

        Returns:
            Generated text.
        """
        response = self.genai_client.models.generate_content(
            model=self.config.llm_model,
            contents=prompt["user"],
            config=types.GenerateContentConfig(
                system_instruction=prompt["system"],
                temperature=self.config.llm_temperature,
                max_output_tokens=self.config.max_output_tokens,
            ),
        )
        return response.text

    def ask(self, question: str, demo_slug: str = DEFAULT_DEMO) -> AskResponse:
        """Answer a question using RAG pipeline.

        Args:
            question: User's question.
            demo_slug: Demo namespace for retrieval.

        Returns:
            AskResponse with answer, sources, and confidence.
        """
        no_info = "I don't have enough information in the available documents to answer that question."

        retrieval = self._retrieve(question, demo_slug=demo_slug)
        if retrieval is None:
            return AskResponse(answer=no_info, sources=[], confidence="low")

        chunks, sources, confidence = retrieval

        prompt = build_prompt(chunks, question)
        answer = self._generate(prompt)

        # Override confidence when the LLM itself says it lacks information
        if self._is_no_info_answer(answer):
            confidence = "low"

        return AskResponse(
            answer=answer, sources=sources, confidence=confidence
        )

    async def ask_stream(
        self, question: str, demo_slug: str = DEFAULT_DEMO
    ) -> AsyncGenerator[str, None]:
        """Stream an answer as SSE events.

        Yields sources immediately, then streams LLM tokens, then done.

        Args:
            question: User's question.
            demo_slug: Demo namespace for retrieval.

        Yields:
            SSE-formatted event strings.
        """
        no_info = "I don't have enough information in the available documents to answer that question."

        retrieval = self._retrieve(question, demo_slug=demo_slug)
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

        async for chunk in await self.genai_client.aio.models.generate_content_stream(
            model=self.config.llm_model,
            contents=prompt["user"],
            config=types.GenerateContentConfig(
                system_instruction=prompt["system"],
                temperature=self.config.llm_temperature,
                max_output_tokens=self.config.max_output_tokens,
            ),
        ):
            token = chunk.text
            if token:
                full_answer.append(token)
                yield f"event: token\ndata: {json.dumps(token)}\n\n"

        # Override confidence if the LLM declined to answer
        if self._is_no_info_answer("".join(full_answer)):
            override_data = json.dumps({"confidence": "low"})
            yield f"event: confidence_override\ndata: {override_data}\n\n"

        yield "event: done\ndata: [DONE]\n\n"

    def get_demos(self) -> list[DemoInfo]:
        """List all available demos.

        Returns:
            List of DemoInfo objects.
        """
        demos = list_demos()
        return [DemoInfo(slug=d.slug, name=d.name) for d in demos]

    def list_documents(self, demo_slug: str = DEFAULT_DEMO) -> list[DocumentInfo]:
        """List all indexed documents with section counts and freshness metadata.

        Args:
            demo_slug: Demo namespace for Pinecone query.

        Returns:
            List of DocumentInfo objects.
        """
        demo_config = self._demo_config(demo_slug)
        resources_dir = self._resources_dir(demo_slug)
        owner_map = demo_config.document_owners if demo_config else {}

        query_vector = self._embed_query("document overview")

        results = self.index.query(
            vector=query_vector,
            top_k=100,
            include_metadata=True,
            namespace=demo_slug,
        )

        doc_sections: dict[str, set[int]] = {}
        doc_types: dict[str, str] = {}
        doc_slugs: dict[str, str] = {}

        for match in results.matches:
            metadata = match.metadata or {}
            name = metadata.get("source_document", "Unknown")
            doc_type = metadata.get("document_type", "general")
            section = metadata.get("section_number", 0)
            source_file = metadata.get("source_file", "")

            if name not in doc_sections:
                doc_sections[name] = set()
                doc_types[name] = doc_type
                slug = source_file.removesuffix(".md") if source_file else ""
                doc_slugs[name] = slug

            doc_sections[name].add(section)

        documents: list[DocumentInfo] = []
        for name in sorted(doc_sections):
            slug = doc_slugs[name]
            last_updated: str | None = None
            is_stale = False
            owner = owner_map.get(slug, "")

            md_path = Path(resources_dir) / f"{slug}.md"
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

    def get_document(
        self, slug: str, demo_slug: str = DEFAULT_DEMO
    ) -> DocumentContentResponse | None:
        """Get full content and metadata for a single document.

        Args:
            slug: Filename stem (e.g. 'employee-handbook').
            demo_slug: Demo identifier.

        Returns:
            DocumentContentResponse or None if not found.
        """
        demo_config = self._demo_config(demo_slug)
        resources_dir = self._resources_dir(demo_slug)
        data = load_full_document(resources_dir, slug, demo_config=demo_config)
        if data is None:
            return None
        return DocumentContentResponse(**data)

    def health_check(self) -> HealthResponse:
        """Check service health including Pinecone connectivity.

        Returns:
            HealthResponse with status information.
        """
        try:
            query_vector = self._embed_query("health check")
            results = self.index.query(
                vector=query_vector, top_k=1, include_metadata=True
            )
            pinecone_connected = True
            documents_indexed = len(results.matches)
        except Exception:
            logger.exception("Pinecone health check failed")
            pinecone_connected = False
            documents_indexed = 0

        return HealthResponse(
            status="healthy" if pinecone_connected else "degraded",
            pinecone_connected=pinecone_connected,
            documents_indexed=documents_indexed,
        )
