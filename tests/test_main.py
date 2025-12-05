"""
Tests for the RAG system core functionality.

Uses fixtures from conftest.py for mocking external dependencies.
"""

import pytest
from main import LLMBackend, LLMConfig, RAGSystem
from conftest import (
    MockOllamaLLM,
    MockLlamaCpp,
    MockHuggingFacePipeline,
    MockHuggingFaceEmbeddings,
    MockFAISS,
    MockDocument,
)


# =============================================================================
# Initialization Tests
# =============================================================================


def test_initialization_base(rag_system, base_config):
    """Test RAGSystem initialization with default values."""
    assert isinstance(rag_system.llm, MockOllamaLLM)
    assert rag_system.llm.kwargs["model"] == base_config.model_name
    assert rag_system.llm.kwargs["temperature"] == base_config.temperature
    assert isinstance(rag_system.embeddings, MockHuggingFaceEmbeddings)
    assert rag_system.embeddings.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert rag_system.text_splitter.chunk_size == 1000
    assert rag_system.vectorstore is None


def test_initialization_llama_cpp():
    """Test initialization with LLAMA_CPP backend."""
    config = LLMConfig(
        backend=LLMBackend.LLAMA_CPP,
        model_name="test-llama",
        model_path="/path/to/model.gguf",
    )
    system = RAGSystem(llm_config=config)
    assert isinstance(system.llm, MockLlamaCpp)
    assert system.llm.kwargs["model_path"] == "/path/to/model.gguf"
    assert system.llm.kwargs["n_ctx"] == config.context_window


def test_initialization_huggingface():
    """Test initialization with HUGGINGFACE backend."""
    config = LLMConfig(backend=LLMBackend.HUGGINGFACE, model_name="test-hf-model")
    system = RAGSystem(llm_config=config)
    assert isinstance(system.llm, MockHuggingFacePipeline)


def test_initialization_custom_chunks():
    """Test RAGSystem initialization with custom chunking parameters."""
    config = LLMConfig(backend=LLMBackend.OLLAMA, model_name="test-model")
    system = RAGSystem(llm_config=config, chunk_size=500, chunk_overlap=50)
    assert system.text_splitter.chunk_size == 500
    assert system.text_splitter.chunk_overlap == 50


# =============================================================================
# LLMConfig Validation Tests
# =============================================================================


def test_config_validation_llama_cpp_no_path():
    """Test that LLAMA_CPP raises ValueError if model_path is missing."""
    with pytest.raises(ValueError, match="model_path is required for llama.cpp backend"):
        LLMConfig(backend=LLMBackend.LLAMA_CPP, model_name="test-llama")


def test_config_validation_empty_model_name():
    """Test that empty model_name raises ValueError."""
    with pytest.raises(ValueError, match="model_name cannot be empty"):
        LLMConfig(backend=LLMBackend.OLLAMA, model_name="")


def test_config_validation_whitespace_model_name():
    """Test that whitespace-only model_name raises ValueError."""
    with pytest.raises(ValueError, match="model_name cannot be empty"):
        LLMConfig(backend=LLMBackend.OLLAMA, model_name="   ")


def test_config_validation_temperature_too_low():
    """Test that temperature below 0 raises ValueError."""
    with pytest.raises(ValueError, match="temperature must be between"):
        LLMConfig(backend=LLMBackend.OLLAMA, model_name="test", temperature=-0.1)


def test_config_validation_temperature_too_high():
    """Test that temperature above 2 raises ValueError."""
    with pytest.raises(ValueError, match="temperature must be between"):
        LLMConfig(backend=LLMBackend.OLLAMA, model_name="test", temperature=2.5)


def test_config_validation_max_tokens_too_low():
    """Test that max_tokens below 1 raises ValueError."""
    with pytest.raises(ValueError, match="max_tokens must be between"):
        LLMConfig(backend=LLMBackend.OLLAMA, model_name="test", max_tokens=0)


def test_config_validation_max_tokens_too_high():
    """Test that max_tokens above 8192 raises ValueError."""
    with pytest.raises(ValueError, match="max_tokens must be between"):
        LLMConfig(backend=LLMBackend.OLLAMA, model_name="test", max_tokens=10000)


def test_config_validation_context_window_too_low():
    """Test that context_window below 512 raises ValueError."""
    with pytest.raises(ValueError, match="context_window must be between"):
        LLMConfig(backend=LLMBackend.OLLAMA, model_name="test", context_window=256)


def test_config_valid_edge_cases():
    """Test valid edge case values for LLMConfig."""
    # Minimum valid values
    config_min = LLMConfig(
        backend=LLMBackend.OLLAMA,
        model_name="test",
        temperature=0.0,
        max_tokens=1,
        context_window=512,
    )
    assert config_min.temperature == 0.0
    assert config_min.max_tokens == 1

    # Maximum valid values
    config_max = LLMConfig(
        backend=LLMBackend.OLLAMA,
        model_name="test",
        temperature=2.0,
        max_tokens=8192,
        context_window=32768,
    )
    assert config_max.temperature == 2.0
    assert config_max.max_tokens == 8192


# =============================================================================
# Document Loading and Vector Store Tests
# =============================================================================


def test_load_pdf(rag_system, tmp_path):
    """Test loading and splitting a PDF file."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.touch()

    documents = rag_system.load_pdf(str(pdf_file))
    # MockPyPDFLoader returns 2 pages, splitter returns len * 2 = 4 chunks
    assert len(documents) == 4
    assert documents[0].page_content == "chunk_0"
    assert documents[-1].metadata["source"] == "page_3"


def test_load_pdf_file_not_found(rag_system):
    """Test that loading non-existent PDF raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="PDF file not found"):
        rag_system.load_pdf("/nonexistent/path.pdf")


def test_load_pdf_invalid_extension(rag_system, tmp_path):
    """Test that loading non-PDF file raises ValueError."""
    txt_file = tmp_path / "test.txt"
    txt_file.touch()

    with pytest.raises(ValueError, match="Invalid file type"):
        rag_system.load_pdf(str(txt_file))


def test_create_vectorstore(rag_system, mocker):
    """Test creation of the vector store."""
    mock_from_documents = mocker.spy(MockFAISS, "from_documents")

    test_docs = [MockDocument("a"), MockDocument("b"), MockDocument("c")]
    rag_system.create_vectorstore(test_docs)

    assert rag_system.vectorstore is not None
    mock_from_documents.assert_called_once_with(test_docs, rag_system.embeddings)


def test_load_from_pdf_end_to_end(rag_system, mocker):
    """Test the combined load_from_pdf method."""
    mocker.patch.object(
        rag_system, "load_pdf", return_value=[MockDocument("c1"), MockDocument("c2")]
    )
    mocker.patch.object(rag_system, "create_vectorstore")

    rag_system.load_from_pdf("test.pdf")

    rag_system.load_pdf.assert_called_once_with("test.pdf")
    rag_system.create_vectorstore.assert_called_once()
    assert len(rag_system.create_vectorstore.call_args[0][0]) == 2


def test_save_vectorstore(rag_system, mocker):
    """Test saving the vector store."""
    rag_system.vectorstore = MockFAISS(documents=[], embeddings=rag_system.embeddings)
    mock_save_local = mocker.spy(rag_system.vectorstore, "save_local")

    rag_system.save_vectorstore("path/to/save")

    mock_save_local.assert_called_once_with("path/to/save")


def test_save_vectorstore_no_store(rag_system):
    """Test saving when vector store is not initialized."""
    with pytest.raises(ValueError, match="No vector store to save"):
        rag_system.save_vectorstore("path")


def test_load_vectorstore(rag_system, mocker, tmp_path):
    """Test loading the vector store from disk."""
    store_path = tmp_path / "vectorstore"
    store_path.mkdir()

    mock_load_local = mocker.spy(MockFAISS, "load_local")

    rag_system.load_vectorstore(str(store_path))

    assert rag_system.vectorstore is not None
    mock_load_local.assert_called_once_with(
        str(store_path),
        rag_system.embeddings,
        allow_dangerous_deserialization=True,
    )


def test_load_vectorstore_not_found(rag_system):
    """Test loading non-existent vectorstore raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Vector store not found"):
        rag_system.load_vectorstore("/nonexistent/path")


# =============================================================================
# Retrieval and Generation Tests
# =============================================================================


def test_retrieve_context_success(rag_system_with_vectorstore, mocker):
    """Test successful context retrieval."""
    mock_search = mocker.spy(rag_system_with_vectorstore.vectorstore, "similarity_search")
    query = "What is RAG?"

    context = rag_system_with_vectorstore.retrieve_context(query, k=2)

    assert len(context) == 2
    assert context[0].page_content.startswith("Relevant chunk for What is RAG? 1")
    mock_search.assert_called_once_with(query, k=2)


def test_retrieve_context_no_vectorstore(rag_system):
    """Test retrieval raises error if vector store is missing."""
    with pytest.raises(ValueError, match="No documents loaded"):
        rag_system.retrieve_context("query")


def test_generate_answer_full_flow(rag_system_with_vectorstore, mocker):
    """Test the full generate_answer RAG flow."""
    mock_llm_invoke = mocker.spy(rag_system_with_vectorstore.llm, "invoke")

    query = "Explain RAG"
    result = rag_system_with_vectorstore.generate_answer(query, k=2)

    # RAGResponse has answer and sources attributes
    assert hasattr(result, "answer")
    assert hasattr(result, "sources")
    assert result.answer.startswith("Simulated answer based on prompt:")
    assert len(result.sources) == 2

    # Check that the generated prompt contains the context and question
    invoked_prompt = mock_llm_invoke.call_args[0][0]
    assert query in invoked_prompt
    assert "Relevant chunk for Explain RAG 1" in invoked_prompt

    # Check source formatting (Source dataclass)
    assert result.sources[0].metadata["source"] == "doc1"
    assert result.sources[0].content.endswith("...")


def test_build_prompt(rag_system):
    """Test the _build_prompt method."""
    context = "Test context"
    query = "Test question"

    prompt = rag_system._build_prompt(context, query)

    assert "Test context" in prompt
    assert "Test question" in prompt
    assert "Context:" in prompt
    assert "Question:" in prompt
    assert "Answer:" in prompt


def test_rag_response_to_dict(rag_system_with_vectorstore):
    """Test RAGResponse.to_dict() for backward compatibility."""
    result = rag_system_with_vectorstore.generate_answer("test query", k=2)

    # Convert to dict
    result_dict = result.to_dict()

    # Should have same structure as old dict response
    assert "answer" in result_dict
    assert "sources" in result_dict
    assert isinstance(result_dict["sources"], list)
    assert "content" in result_dict["sources"][0]
    assert "metadata" in result_dict["sources"][0]
