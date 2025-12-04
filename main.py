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

from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

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
    """Configuration for the LLM"""
    backend: LLMBackend
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 512
    model_path: Optional[str] = None  # For llama.cpp
    context_window: int = 2048


class RAGSystem:
    """RAG system with configurable local LLM support"""
    
    def __init__(
        self,
        llm_config: LLMConfig,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_size: int = 100,
        chunk_overlap: int = 20
    ):
        """
        Initialize RAG system
        
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
            length_function=len
        )
        self.vectorstore = None
        
    def _initialize_llm(self):
        """Initialize the LLM based on backend configuration"""
        if self.llm_config.backend == LLMBackend.OLLAMA:
            return OllamaLLM(
                model=self.llm_config.model_name,
                temperature=self.llm_config.temperature,
                num_predict=self.llm_config.max_tokens
            )
            
        elif self.llm_config.backend == LLMBackend.LLAMA_CPP:
            from langchain_community.llms import LlamaCpp
            if not self.llm_config.model_path:
                raise ValueError("model_path required for llama.cpp backend")
            return LlamaCpp(
                model_path=self.llm_config.model_path,
                temperature=self.llm_config.temperature,
                max_tokens=self.llm_config.max_tokens,
                n_ctx=self.llm_config.context_window
            )
            
        elif self.llm_config.backend == LLMBackend.HUGGINGFACE:
            from langchain_community.llms import HuggingFacePipeline
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
            
            tokenizer = AutoTokenizer.from_pretrained(self.llm_config.model_name)
            model = AutoModelForCausalLM.from_pretrained(self.llm_config.model_name)
            
            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=self.llm_config.max_tokens,
                temperature=self.llm_config.temperature
            )
            return HuggingFacePipeline(pipeline=pipe)
        
        else:
            raise ValueError(f"Unsupported backend: {self.llm_config.backend}")
    
    def load_pdf(self, pdf_path: str) -> List[Document]:
        """Load and split PDF document"""
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        splits = self.text_splitter.split_documents(documents)
        print(f"Loaded {len(documents)} pages, split into {len(splits)} chunks")
        return splits
    
    def create_vectorstore(self, documents: List[Document]):
        """Create vector store from documents"""
        self.vectorstore = FAISS.from_documents(documents, self.embeddings)
        print(f"Created vector store with {len(documents)} documents")
    
    def load_from_pdf(self, pdf_path: str):
        """Load PDF and create vector store in one step"""
        documents = self.load_pdf(pdf_path)
        self.create_vectorstore(documents)
    
    def retrieve_context(self, query: str, k: int = 4) -> List[Document]:
        """Retrieve relevant documents for a query"""
        if not self.vectorstore:
            raise ValueError("No documents loaded. Call load_from_pdf first.")
        return self.vectorstore.similarity_search(query, k=k)
    
    def generate_answer(self, query: str, k: int = 4) -> dict:
        """
        Generate answer using RAG
        
        Returns:
            dict with 'answer' and 'sources'
        """
        # Retrieve relevant context
        relevant_docs = self.retrieve_context(query, k=k)
        
        # Build context from retrieved documents
        context = "\n\n".join([doc.page_content for doc in relevant_docs])
        
        # Create prompt
        prompt = f"""Based on the following context, answer the question. If the answer cannot be found in the context, say so.

Context:
{context}

Question: {query}

Answer:"""
        
        # Generate response
        response = self.llm.invoke(prompt)
        
        return {
            "answer": response.strip(),
            "sources": [
                {
                    "content": doc.page_content[:200] + "...",
                    "metadata": doc.metadata
                }
                for doc in relevant_docs
            ]
        }
    
    def save_vectorstore(self, path: str):
        """Save vector store to disk"""
        if not self.vectorstore:
            raise ValueError("No vector store to save")
        self.vectorstore.save_local(path)
        print(f"Vector store saved to {path}")
    
    def load_vectorstore(self, path: str):
        """Load vector store from disk"""
        self.vectorstore = FAISS.load_local(
            path, 
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        print(f"Vector store loaded from {path}")


def main():
    """Example usage"""
    
    # Example 1: Using Ollama (easiest option)
    print("=" * 50)
    print("Example 1: Ollama Backend")
    print("=" * 50)
    
    config_ollama = LLMConfig(
        backend=LLMBackend.OLLAMA,
        model_name="llama3.1:latest",  # or "mistral", "phi", etc.
        temperature=0.7,
        max_tokens=512
    )
    
    rag_ollama = RAGSystem(llm_config=config_ollama)
    
    # Load PDF and create knowledge base
    rag_ollama.load_from_pdf("resources/Grokking Algorithms.pdf")
    
    # Query the system
    result = rag_ollama.generate_answer("What is this document about?")
    print(f"Answer: {result['answer']}\n")
    print(f"Sources: {len(result['sources'])} documents used")
    
    
    # Example 2: Using llama.cpp
    # print("\n" + "=" * 50)
    # print("Example 2: llama.cpp Backend")
    # print("=" * 50)
    
    # config_llamacpp = LLMConfig(
    #     backend=LLMBackend.LLAMA_CPP,
    #     model_name="llama-2-7b",
    #     model_path="/path/to/model.gguf",  # Update this path
    #     temperature=0.7,
    #     max_tokens=512,
    #     context_window=2048
    # )
    
    # rag_llamacpp = RAGSystem(llm_config=config_llamacpp)
    
    
    # Example 3: Using Hugging Face
    # print("\n" + "=" * 50)
    # print("Example 3: Hugging Face Backend")
    # print("=" * 50)
    
    # config_hf = LLMConfig(
    #     backend=LLMBackend.HUGGINGFACE,
    #     model_name="gpt2",  # or "microsoft/phi-2", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    #     temperature=0.7,
    #     max_tokens=256
    # )
    
    # rag_hf = RAGSystem(llm_config=config_hf)
    
    
    print("=" * 50)


if __name__ == "__main__":
    main()
