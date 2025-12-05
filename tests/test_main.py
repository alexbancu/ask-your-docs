import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from main module
from main import LLMBackend, LLMConfig, RAGSystem

# --- Start Mocking Definitions ---

# Mock LangChain Document
class Document:
    def __init__(self, page_content, metadata=None):
        self.page_content = page_content
        self.metadata = metadata if metadata is not None else {}

# Mock HuggingFaceEmbeddings
class MockHuggingFaceEmbeddings:
    def __init__(self, model_name):
        self.model_name = model_name

# Mock Text Splitter
class MockRecursiveCharacterTextSplitter:
    def __init__(self, chunk_size, chunk_overlap, length_function):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function

    def split_documents(self, documents):
        # Simulate splitting: returns a list of Documents (chunks)
        return [Document(f"chunk_{i}", {"source": f"page_{i}"}) for i in range(len(documents) * 2)]

# Mock LLMs
class MockLLM:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def invoke(self, prompt):
        # Simulate LLM response
        return f"Simulated answer based on prompt: {prompt}"

class MockOllamaLLM(MockLLM): pass
class MockLlamaCpp(MockLLM): pass
class MockHuggingFacePipeline(MockLLM): pass

# Mock PDF Loader
class MockPyPDFLoader:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def load(self):
        # Simulate loading 2 pages/documents
        return [
            Document("Content of page 1"),
            Document("Content of page 2")
        ]

# Mock Vector Store (FAISS)
class MockFAISS:
    def __init__(self, documents, embeddings):
        self.documents = documents
        self.embeddings = embeddings

    @classmethod
    def from_documents(cls, documents, embeddings):
        return cls(documents, embeddings)

    def similarity_search(self, query, k):
        # Simulate retrieval: return top k documents
        return [
            Document(f"Relevant chunk for {query} 1", {"source": "doc1"}),
            Document(f"Relevant chunk for {query} 2", {"source": "doc2"})
        ][:k]

    def save_local(self, path):
        pass # Simulate saving

    @classmethod
    def load_local(cls, path, embeddings, allow_dangerous_deserialization):
        return cls(documents=[Document("loaded_doc")], embeddings=embeddings)


# Patch the external dependencies with our mock objects
@pytest.fixture(autouse=True)
def patch_rag_dependencies(mocker):
    # Patch all the external classes used in RAGSystem (module-level imports only)
    mocker.patch('main.HuggingFaceEmbeddings', MockHuggingFaceEmbeddings)
    mocker.patch('main.RecursiveCharacterTextSplitter', MockRecursiveCharacterTextSplitter)
    mocker.patch('main.OllamaLLM', MockOllamaLLM)
    mocker.patch('main.PyPDFLoader', MockPyPDFLoader)
    mocker.patch('main.FAISS', MockFAISS)

    # Patch lazy imports inside _initialize_llm method
    mocker.patch('langchain_community.llms.LlamaCpp', MockLlamaCpp)
    mocker.patch('langchain_community.llms.HuggingFacePipeline', MockHuggingFacePipeline)
    mocker.patch('transformers.AutoTokenizer', MagicMock())
    mocker.patch('transformers.AutoModelForCausalLM', MagicMock())
    mocker.patch('transformers.pipeline', MagicMock())



@pytest.fixture
def base_config():
    """Returns a basic LLMConfig for Ollama"""
    return LLMConfig(backend=LLMBackend.OLLAMA, model_name="test-model")

@pytest.fixture
def rag_system(base_config):
    """Returns an initialized RAGSystem instance"""
    return RAGSystem(llm_config=base_config)

# --- End Mocking Definitions ---

## 🧪 Initialization Tests

def test_initialization_base(rag_system, base_config):
    """Test RAGSystem initialization with default values"""
    assert isinstance(rag_system.llm, MockOllamaLLM)
    assert rag_system.llm.kwargs['model'] == base_config.model_name
    assert rag_system.llm.kwargs['temperature'] == base_config.temperature
    assert isinstance(rag_system.embeddings, MockHuggingFaceEmbeddings)
    assert rag_system.embeddings.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert rag_system.text_splitter.chunk_size == 1000
    assert rag_system.vectorstore is None

def test_initialization_llama_cpp():
    """Test initialization with LLAMA_CPP backend"""
    config = LLMConfig(
        backend=LLMBackend.LLAMA_CPP, 
        model_name="test-llama", 
        model_path="/path/to/model.gguf"
    )
    system = RAGSystem(llm_config=config)
    assert isinstance(system.llm, MockLlamaCpp)
    assert system.llm.kwargs['model_path'] == "/path/to/model.gguf"
    assert system.llm.kwargs['n_ctx'] == config.context_window

def test_initialization_llama_cpp_no_path():
    """Test that LLAMA_CPP raises ValueError if model_path is missing"""
    config = LLMConfig(backend=LLMBackend.LLAMA_CPP, model_name="test-llama")
    with pytest.raises(ValueError, match="model_path required for llama.cpp backend"):
        RAGSystem(llm_config=config)

def test_initialization_huggingface():
    """Test initialization with HUGGINGFACE backend"""
    config = LLMConfig(backend=LLMBackend.HUGGINGFACE, model_name="test-hf-model")
    system = RAGSystem(llm_config=config)
    assert isinstance(system.llm, MockHuggingFacePipeline)

def test_initialization_custom_chunks():
    """Test RAGSystem initialization with custom chunking parameters"""
    config = LLMConfig(backend=LLMBackend.OLLAMA, model_name="test-model")
    system = RAGSystem(llm_config=config, chunk_size=500, chunk_overlap=50)
    assert system.text_splitter.chunk_size == 500
    assert system.text_splitter.chunk_overlap == 50

## 💾 Document Loading and Vector Store Tests

def test_load_pdf(rag_system):
    """Test loading and splitting a PDF file"""
    documents = rag_system.load_pdf("test.pdf")
    # MockPyPDFLoader returns 2 pages. MockRecursiveCharacterTextSplitter 
    # returns len(documents) * 2 chunks. So 2 * 2 = 4 chunks.
    assert len(documents) == 4
    assert documents[0].page_content == "chunk_0"
    assert documents[-1].metadata["source"] == "page_3"

def test_create_vectorstore(rag_system, mocker):
    """Test creation of the vector store"""
    mock_from_documents = mocker.spy(MockFAISS, 'from_documents')
    
    test_docs = [Document("a"), Document("b"), Document("c")]
    rag_system.create_vectorstore(test_docs)
    
    assert rag_system.vectorstore is not None
    mock_from_documents.assert_called_once_with(test_docs, rag_system.embeddings)

def test_load_from_pdf_end_to_end(rag_system, mocker):
    """Test the combined load_from_pdf method"""
    mocker.patch.object(rag_system, 'load_pdf', return_value=[Document("c1"), Document("c2")])
    mocker.patch.object(rag_system, 'create_vectorstore')
    
    rag_system.load_from_pdf("test.pdf")
    
    rag_system.load_pdf.assert_called_once_with("test.pdf")
    # create_vectorstore should be called with the return value of load_pdf
    rag_system.create_vectorstore.assert_called_once()
    assert len(rag_system.create_vectorstore.call_args[0][0]) == 2 # Check docs passed to create_vectorstore

def test_save_vectorstore(rag_system, mocker):
    """Test saving the vector store"""
    rag_system.vectorstore = MockFAISS(documents=[], embeddings=rag_system.embeddings)
    mock_save_local = mocker.spy(rag_system.vectorstore, 'save_local')

    rag_system.save_vectorstore("path/to/save")
    
    mock_save_local.assert_called_once_with("path/to/save")

def test_save_vectorstore_no_store(rag_system):
    """Test saving when vector store is not initialized"""
    with pytest.raises(ValueError, match="No vector store to save"):
        rag_system.save_vectorstore("path")

def test_load_vectorstore(rag_system, mocker):
    """Test loading the vector store from disk"""
    mock_load_local = mocker.spy(MockFAISS, 'load_local')

    rag_system.load_vectorstore("path/to/load")

    assert rag_system.vectorstore is not None
    mock_load_local.assert_called_once_with(
        "path/to/load", 
        rag_system.embeddings, 
        allow_dangerous_deserialization=True
    )

## 💬 Retrieval and Generation Tests

def initialize_rag_for_query(rag_system):
    """Helper to initialize vectorstore for query tests"""
    rag_system.vectorstore = MockFAISS(documents=[], embeddings=rag_system.embeddings)
    return rag_system

def test_retrieve_context_success(rag_system, mocker):
    """Test successful context retrieval"""
    rag_system = initialize_rag_for_query(rag_system)
    mock_search = mocker.spy(rag_system.vectorstore, 'similarity_search')
    query = "What is RAG?"
    
    context = rag_system.retrieve_context(query, k=2)
    
    assert len(context) == 2
    assert context[0].page_content.startswith("Relevant chunk for What is RAG? 1")
    mock_search.assert_called_once_with(query, k=2)

def test_retrieve_context_no_vectorstore(rag_system):
    """Test retrieval raises error if vector store is missing"""
    with pytest.raises(ValueError, match="No documents loaded. Call load_from_pdf first."):
        rag_system.retrieve_context("query")

def test_generate_answer_full_flow(rag_system, mocker):
    """Test the full generate_answer RAG flow"""
    rag_system = initialize_rag_for_query(rag_system)
    mock_llm_invoke = mocker.spy(rag_system.llm, 'invoke')
    
    query = "Explain RAG"
    result = rag_system.generate_answer(query, k=2)
    
    assert "answer" in result
    assert "sources" in result
    assert result["answer"].startswith("Simulated answer based on prompt:")
    assert len(result["sources"]) == 2
    
    # Check that the generated prompt contains the context and question
    invoked_prompt = mock_llm_invoke.call_args[0][0]
    assert query in invoked_prompt
    assert "Relevant chunk for Explain RAG 1" in invoked_prompt
    
    # Check source formatting
    assert result["sources"][0]["metadata"]["source"] == "doc1"
    assert result["sources"][0]["content"].endswith("...")
