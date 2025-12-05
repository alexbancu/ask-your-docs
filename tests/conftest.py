"""
Shared test fixtures and mocks for RAG system tests.

This module provides reusable mock objects and pytest fixtures
that can be used across all test files.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import LLMBackend, LLMConfig, RAGSystem


# =============================================================================
# Mock Classes
# =============================================================================


class MockDocument:
    """Mock LangChain Document."""

    def __init__(self, page_content: str, metadata: dict = None):
        self.page_content = page_content
        self.metadata = metadata if metadata is not None else {}


class MockHuggingFaceEmbeddings:
    """Mock HuggingFace embeddings."""

    def __init__(self, model_name: str):
        self.model_name = model_name


class MockRecursiveCharacterTextSplitter:
    """Mock text splitter."""

    def __init__(self, chunk_size: int, chunk_overlap: int, length_function):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function

    def split_documents(self, documents):
        """Simulate splitting: returns len(documents) * 2 chunks."""
        return [
            MockDocument(f"chunk_{i}", {"source": f"page_{i}"})
            for i in range(len(documents) * 2)
        ]


class MockLLM:
    """Base mock LLM."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def invoke(self, prompt: str) -> str:
        """Simulate LLM response."""
        return f"Simulated answer based on prompt: {prompt}"


class MockOllamaLLM(MockLLM):
    """Mock Ollama LLM."""

    pass


class MockLlamaCpp(MockLLM):
    """Mock LlamaCpp LLM."""

    pass


class MockHuggingFacePipeline(MockLLM):
    """Mock HuggingFace Pipeline LLM."""

    pass


class MockPyPDFLoader:
    """Mock PDF loader."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def load(self):
        """Simulate loading 2 pages."""
        return [
            MockDocument("Content of page 1"),
            MockDocument("Content of page 2"),
        ]


class MockFAISS:
    """Mock FAISS vector store."""

    def __init__(self, documents, embeddings):
        self.documents = documents
        self.embeddings = embeddings

    @classmethod
    def from_documents(cls, documents, embeddings):
        return cls(documents, embeddings)

    def similarity_search(self, query: str, k: int):
        """Simulate retrieval: return top k documents."""
        return [
            MockDocument(f"Relevant chunk for {query} 1", {"source": "doc1"}),
            MockDocument(f"Relevant chunk for {query} 2", {"source": "doc2"}),
        ][:k]

    def save_local(self, path: str):
        """Simulate saving."""
        pass

    @classmethod
    def load_local(cls, path, embeddings, allow_dangerous_deserialization):
        return cls(documents=[MockDocument("loaded_doc")], embeddings=embeddings)


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def patch_rag_dependencies(mocker):
    """Patch all external dependencies with mock objects."""
    # Patch module-level imports in main
    mocker.patch("main.HuggingFaceEmbeddings", MockHuggingFaceEmbeddings)
    mocker.patch("main.RecursiveCharacterTextSplitter", MockRecursiveCharacterTextSplitter)
    mocker.patch("main.OllamaLLM", MockOllamaLLM)
    mocker.patch("main.PyPDFLoader", MockPyPDFLoader)
    mocker.patch("main.FAISS", MockFAISS)

    # Patch lazy imports inside _initialize_llm method
    mocker.patch("langchain_community.llms.LlamaCpp", MockLlamaCpp)
    mocker.patch("langchain_community.llms.HuggingFacePipeline", MockHuggingFacePipeline)
    mocker.patch("transformers.AutoTokenizer", MagicMock())
    mocker.patch("transformers.AutoModelForCausalLM", MagicMock())
    mocker.patch("transformers.pipeline", MagicMock())


@pytest.fixture
def base_config():
    """Returns a basic LLMConfig for Ollama."""
    return LLMConfig(backend=LLMBackend.OLLAMA, model_name="test-model")


@pytest.fixture
def rag_system(base_config):
    """Returns an initialized RAGSystem instance."""
    return RAGSystem(llm_config=base_config)


@pytest.fixture
def rag_system_with_vectorstore(rag_system):
    """Returns a RAGSystem with an initialized vectorstore."""
    rag_system.vectorstore = MockFAISS(documents=[], embeddings=rag_system.embeddings)
    return rag_system
