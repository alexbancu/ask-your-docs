"""Cloud configuration for the RAG API service."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class CloudConfig:
    """Configuration for cloud RAG service loaded from environment variables.

    Attributes:
        google_api_key: Google API key for Gemini LLM.
        pinecone_api_key: Pinecone API key for vector store.
        pinecone_index_name: Name of the Pinecone index.
        embedding_model: HuggingFace embedding model name.
        llm_model: Gemini model name.
        llm_temperature: Temperature for LLM generation.
        retrieval_k: Number of chunks to retrieve.
    """

    google_api_key: str
    pinecone_api_key: str
    pinecone_index_name: str = "acme-corp-knowledge"
    embedding_model: str = "all-MiniLM-L6-v2"
    llm_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.3
    retrieval_k: int = 6


def load_config() -> CloudConfig:
    """Load configuration from environment variables.

    Returns:
        CloudConfig instance.

    Raises:
        ValueError: If required environment variables are missing.
    """
    load_dotenv()

    google_api_key = os.getenv("GOOGLE_API_KEY", "")
    pinecone_api_key = os.getenv("PINECONE_API_KEY", "")
    pinecone_index_name = os.getenv("PINECONE_INDEX_NAME", "acme-corp-knowledge")

    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY environment variable is required")

    return CloudConfig(
        google_api_key=google_api_key,
        pinecone_api_key=pinecone_api_key,
        pinecone_index_name=pinecone_index_name,
    )
