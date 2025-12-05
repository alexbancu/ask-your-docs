"""
Configuration constants and defaults for the RAG system.

Centralizes magic numbers and default values for easier maintenance.
"""

from pathlib import Path

# ============================================================
# Embedding Configuration
# ============================================================
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ============================================================
# Chunking Configuration
# ============================================================
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200

# ============================================================
# LLM Configuration
# ============================================================
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 512
DEFAULT_CONTEXT_WINDOW = 2048

# Validation ranges
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0
MIN_MAX_TOKENS = 1
MAX_MAX_TOKENS = 8192
MIN_CONTEXT_WINDOW = 512
MAX_CONTEXT_WINDOW = 32768

# ============================================================
# Retrieval Configuration
# ============================================================
DEFAULT_RETRIEVAL_K = 4
SOURCE_SNIPPET_LENGTH = 200

# ============================================================
# Ollama Configuration
# ============================================================
DEFAULT_OLLAMA_HOST = "localhost"
DEFAULT_OLLAMA_PORT = 11434
DEFAULT_OLLAMA_MODEL = "llama3.1:latest"

# ============================================================
# Path Configuration
# ============================================================
PROJECT_ROOT = Path(__file__).parent
DEFAULT_PDF_PATH = PROJECT_ROOT / "resources" / "Grokking Algorithms.pdf"
DEFAULT_VECTORSTORE_PATH = PROJECT_ROOT / "vectorstore"
