"""
RAG (Retrieval-Augmented Generation) Solution with Local LLM Support

This implementation supports multiple local LLM backends:
- Ollama (recommended for ease of use)
- llama.cpp via llama-cpp-python
- Hugging Face Transformers

Requirements:
pip install langchain langchain-community sentence-transformers chromadb pypdf faiss-cpu

For specific LLM backends:
- Ollama: Install from https://ollama.ai
- llama.cpp: pip install llama-cpp-python
- Transformers: pip install transformers torch
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_CONTEXT_WINDOW,
    MIN_TEMPERATURE,
    MAX_TEMPERATURE,
    MIN_MAX_TOKENS,
    MAX_MAX_TOKENS,
    MIN_CONTEXT_WINDOW,
    MAX_CONTEXT_WINDOW,
    SOURCE_SNIPPET_LENGTH,
)

# Configure module logger
logger = logging.getLogger(__name__)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_ollama import OllamaLLM


class LLMBackend(Enum):
    """Supported LLM backends"""
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"
    HUGGINGFACE = "huggingface"


@dataclass
class LLMConfig:
    """Configuration for the LLM with validation."""
    backend: LLMBackend
    model_name: str
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    model_path: Optional[str] = None  # Required for llama.cpp backend
    context_window: int = DEFAULT_CONTEXT_WINDOW

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not isinstance(self.backend, LLMBackend):
            raise ValueError(
                f"Invalid backend type: {type(self.backend)}. "
                f"Expected LLMBackend enum, got one of: {[b.value for b in LLMBackend]}"
            )

        if not self.model_name or not self.model_name.strip():
            raise ValueError("model_name cannot be empty")

        if not MIN_TEMPERATURE <= self.temperature <= MAX_TEMPERATURE:
            raise ValueError(
                f"temperature must be between {MIN_TEMPERATURE} and {MAX_TEMPERATURE}, "
                f"got {self.temperature}"
            )

        if not MIN_MAX_TOKENS <= self.max_tokens <= MAX_MAX_TOKENS:
            raise ValueError(
                f"max_tokens must be between {MIN_MAX_TOKENS} and {MAX_MAX_TOKENS}, "
                f"got {self.max_tokens}"
            )

        if not MIN_CONTEXT_WINDOW <= self.context_window <= MAX_CONTEXT_WINDOW:
            raise ValueError(
                f"context_window must be between {MIN_CONTEXT_WINDOW} and {MAX_CONTEXT_WINDOW}, "
                f"got {self.context_window}"
            )

        if self.backend == LLMBackend.LLAMA_CPP and not self.model_path:
            raise ValueError(
                "model_path is required for llama.cpp backend. "
                "Provide the path to your .gguf model file."
            )


class RAGSystem:
    """RAG system with configurable local LLM support."""

    def __init__(
        self,
        llm_config: LLMConfig,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        """
        Initialize RAG system.

        Args:
            llm_config: Configuration for the LLM
            embedding_model: Name of the sentence transformer model for embeddings
            chunk_size: Size of text chunks for splitting
            chunk_overlap: Overlap between chunks
        """
        self.llm_config = llm_config
        self.llm = self._initialize_llm()
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        self.vectorstore: Optional[FAISS] = None
        logger.debug(
            "RAGSystem initialized with backend=%s, model=%s",
            llm_config.backend.value,
            llm_config.model_name,
        )
        
    def _initialize_llm(self) -> Any:
        """Initialize the LLM based on backend configuration."""
        backend = self.llm_config.backend
        logger.info("Initializing LLM backend: %s", backend.value)

        if backend == LLMBackend.OLLAMA:
            return OllamaLLM(
                model=self.llm_config.model_name,
                temperature=self.llm_config.temperature,
                num_predict=self.llm_config.max_tokens,
            )

        elif backend == LLMBackend.LLAMA_CPP:
            from langchain_community.llms import LlamaCpp

            # model_path validation done in LLMConfig.__post_init__
            return LlamaCpp(
                model_path=self.llm_config.model_path,
                temperature=self.llm_config.temperature,
                max_tokens=self.llm_config.max_tokens,
                n_ctx=self.llm_config.context_window,
            )

        elif backend == LLMBackend.HUGGINGFACE:
            from langchain_community.llms import HuggingFacePipeline
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

            logger.info("Loading HuggingFace model: %s", self.llm_config.model_name)
            tokenizer = AutoTokenizer.from_pretrained(self.llm_config.model_name)
            model = AutoModelForCausalLM.from_pretrained(self.llm_config.model_name)

            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=self.llm_config.max_tokens,
                temperature=self.llm_config.temperature,
            )
            return HuggingFacePipeline(pipeline=pipe)

        else:
            raise ValueError(
                f"Unsupported backend: {backend}. "
                f"Supported backends: {[b.value for b in LLMBackend]}"
            )
    
    def load_pdf(self, pdf_path: str) -> List[Document]:
        """Load and split PDF document into chunks."""
        from pathlib import Path

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(
                f"PDF file not found: {pdf_path}. "
                "Please provide a valid path to the PDF file."
            )
        if not path.suffix.lower() == ".pdf":
            raise ValueError(
                f"Invalid file type: {path.suffix}. Expected a .pdf file."
            )

        logger.info("Loading PDF: %s", pdf_path)
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        splits = self.text_splitter.split_documents(documents)
        logger.info("Loaded %d pages, split into %d chunks", len(documents), len(splits))
        return splits

    def create_vectorstore(self, documents: List[Document]) -> None:
        """Create vector store from documents."""
        logger.info("Creating vector store from %d documents", len(documents))
        self.vectorstore = FAISS.from_documents(documents, self.embeddings)
        logger.info("Vector store created successfully")

    def load_from_pdf(self, pdf_path: str) -> None:
        """Load PDF and create vector store in one step."""
        documents = self.load_pdf(pdf_path)
        self.create_vectorstore(documents)

    def retrieve_context(self, query: str, k: int = 4) -> List[Document]:
        """Retrieve relevant documents for a query."""
        if self.vectorstore is None:
            raise ValueError(
                "No documents loaded. Call load_from_pdf() or load_vectorstore() first."
            )
        logger.debug("Retrieving %d documents for query: %s", k, query[:50])
        return self.vectorstore.similarity_search(query, k=k)

    def generate_answer(self, query: str, k: int = 4) -> Dict[str, Any]:
        """
        Generate answer using RAG.

        Args:
            query: The question to answer
            k: Number of chunks to retrieve

        Returns:
            Dict with 'answer' and 'sources'
        """
        logger.debug("Generating answer for query: %s", query[:50])
        relevant_docs = self.retrieve_context(query, k=k)

        # Build context from retrieved documents
        context = "\n\n".join([doc.page_content for doc in relevant_docs])

        # Create prompt
        prompt = self._build_prompt(context, query)

        # Generate response
        logger.debug("Invoking LLM with prompt length: %d chars", len(prompt))
        response = self.llm.invoke(prompt)

        return {
            "answer": response.strip(),
            "sources": [
                {
                    "content": doc.page_content[:SOURCE_SNIPPET_LENGTH] + "...",
                    "metadata": doc.metadata,
                }
                for doc in relevant_docs
            ],
        }

    def _build_prompt(self, context: str, query: str) -> str:
        """Build the prompt for the LLM."""
        return f"""Based on the following context, answer the question. If the answer cannot be found in the context, say so.

Context:
{context}

Question: {query}

Answer:"""
    
    def save_vectorstore(self, path: str) -> None:
        """Save vector store to disk."""
        if self.vectorstore is None:
            raise ValueError(
                "No vector store to save. "
                "Load documents with load_from_pdf() first."
            )
        self.vectorstore.save_local(path)
        logger.info("Vector store saved to: %s", path)
    
    def load_vectorstore(self, path: str) -> None:
        """
        Load vector store from disk.

        Note: Uses allow_dangerous_deserialization=True for FAISS pickle loading.
        Only load vectorstores from trusted sources.
        """
        from pathlib import Path

        store_path = Path(path)
        if not store_path.exists():
            raise FileNotFoundError(
                f"Vector store not found at: {path}. "
                "Create one with load_from_pdf() first."
            )

        logger.info("Loading vector store from: %s", path)
        self.vectorstore = FAISS.load_local(
            path,
            self.embeddings,
            allow_dangerous_deserialization=True,
        )
        logger.info("Vector store loaded successfully")


def main() -> None:
    """Example usage demonstrating the RAG system."""
    from config import DEFAULT_PDF_PATH, DEFAULT_OLLAMA_MODEL

    # Configure logging for demo
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 50)
    print("RAG System Demo - Ollama Backend")
    print("=" * 50)

    config = LLMConfig(
        backend=LLMBackend.OLLAMA,
        model_name=DEFAULT_OLLAMA_MODEL,
    )

    rag = RAGSystem(llm_config=config)

    # Load PDF and create knowledge base
    rag.load_from_pdf(str(DEFAULT_PDF_PATH))

    # Query the system
    result = rag.generate_answer("What is this document about?", k=10)
    print(f"\n{'=' * 60}")
    print("FINAL ANSWER")
    print("=" * 60)
    print(f"Answer: {result['answer']}\n")
    print(f"Sources: {len(result['sources'])} documents used")
    print("=" * 60)


if __name__ == "__main__":
    main()
