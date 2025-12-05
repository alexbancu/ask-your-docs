# CLAUDE.md - RAG Project Guardrails

## Project Overview

**What**: A Retrieval-Augmented Generation (RAG) system built with Python, LangChain, FAISS, and local LLMs (Ollama, llama.cpp, HuggingFace).

**Why**: To enable semantic search and question-answering over PDF documents using local LLM backends for privacy and cost efficiency.

**How**: Uses sentence-transformers for embeddings, FAISS for vector storage, and configurable LLM backends for generation.

---

## Tech Stack

- **Python**: 3.12+
- **Package Manager**: uv (use `uv sync` to install dependencies, `uv run` to execute)
- **RAG Framework**: LangChain + LangChain Community
- **Vector Store**: FAISS (faiss-cpu)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **LLM Backends**: Ollama (primary), llama.cpp, HuggingFace Transformers
- **Document Loading**: pypdf
- **Testing**: pytest + pytest-mock
- **Linting**: ruff
- **Type Checking**: mypy

---

## Project Structure

```
service-gest-rag/
├── main.py              # Core RAGSystem implementation
├── tests/
│   └── test_main.py     # Unit tests with mocks
├── resources/           # PDF documents for ingestion
├── pyproject.toml       # Project config and dependencies
├── uv.lock              # Locked dependencies
└── .venv/               # Virtual environment (uv-managed)
```

---

## Development Commands

```bash
# Install dependencies
uv sync

# Run the main script
uv run python main.py

# Run tests
uv run pytest tests/ -v

# Run linting
uv run ruff check .

# Run type checking
uv run mypy .

# Format code
uv run ruff format .
```

---

## Python Best Practices

### Code Style (PEP 8)
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 88 characters (Black/Ruff default)
- Use snake_case for functions, variables, and modules
- Use PascalCase for classes
- Use SCREAMING_SNAKE_CASE for constants
- Imports at top of file, grouped: stdlib → third-party → local

### Type Hints (Required)
- All function signatures MUST have type hints
- Use `from typing import` for complex types (List, Optional, Dict, etc.)
- Use dataclasses with type annotations for configuration objects
- Example:
  ```python
  def generate_answer(self, query: str, k: int = 4) -> dict:
  ```

### Error Handling
- Use specific exception types, not bare `except:`
- Log exceptions with full stack traces using `logger.exception()`
- Raise `ValueError` for invalid arguments
- Raise custom exceptions for domain-specific errors
- Always validate inputs at public API boundaries

### Logging
- Use `logging` module, never `print()` in production code
- Configure logging once at application entry point
- Use appropriate levels: DEBUG (dev), INFO (production), ERROR (failures)
- Use structured logging (JSON) for production deployments
- Never log sensitive data (API keys, PII, credentials)

### Documentation
- All public classes and functions MUST have docstrings
- Use Google-style docstrings format:
  ```python
  def method(self, arg: str) -> bool:
      """Short description.

      Args:
          arg: Description of argument.

      Returns:
          Description of return value.

      Raises:
          ValueError: When arg is invalid.
      """
  ```

---

## RAG Architecture Best Practices

### Chunking Strategy
- **Optimal chunk size**: 256-512 tokens (currently 1000 chars - consider reducing)
- **Overlap**: 10-20% of chunk size (currently 200 chars = 20%)
- Use `RecursiveCharacterTextSplitter` for general text
- Preserve document structure: keep headers with their content
- Test different strategies and measure retrieval accuracy

### Embedding Best Practices
- Use domain-appropriate embedding models
- Ensure chunk size < embedding model's token limit (512 for MiniLM)
- Cache embeddings to avoid recomputation
- Consider fine-tuning embeddings for domain-specific vocabulary

### Retrieval Best Practices
- Start with k=4-10 retrieved chunks
- Implement hybrid search (dense + sparse/BM25) for better recall
- Add metadata filtering when applicable
- Track retrieval metrics: recall, precision, MRR, NDCG

### Prompt Engineering
- Keep prompts clear and structured
- Include explicit instructions for handling missing information
- Use delimiters to separate context from question
- Consider adding few-shot examples for complex tasks

---

## Security Guardrails

### Prompt Injection Prevention
- Validate and sanitize all user inputs
- Use input length limits
- Implement output filtering for sensitive patterns
- Never trust retrieved content as instructions

### Data Privacy
- Anonymize PII before indexing
- Implement access control for sensitive documents
- Use metadata tagging for document sensitivity levels
- Audit all data access patterns

### Vector Store Security
- Use `allow_dangerous_deserialization=True` only with trusted sources
- Validate vector store integrity on load
- Implement backup and recovery procedures

### Secrets Management
- Never commit API keys, credentials, or tokens
- Use environment variables or secret managers
- Add `.env` files to `.gitignore`
- Rotate credentials regularly

---

## Testing Best Practices

### Test Structure
- Use pytest fixtures for common setup
- Mock all external dependencies (LLMs, embeddings, file I/O)
- Test each component in isolation
- Include integration tests for full RAG pipeline

### Test Categories
```python
# Unit tests - fast, isolated
def test_chunk_splitting():
    ...

# Integration tests - slower, real components
def test_full_rag_pipeline():
    ...

# Evaluation tests - measure quality
def test_retrieval_accuracy():
    ...
```

### RAG Evaluation Metrics
- **Retrieval**: Context relevancy, recall@k
- **Generation**: Faithfulness, answer relevancy, hallucination rate
- Use frameworks like DeepEval or RAGAS for LLM evaluation
- Run evaluations in CI/CD pipelines

### Mock Patterns
- Mock LLM responses for deterministic tests
- Mock embedding models to avoid downloads in CI
- Use fixtures for reusable mock configurations

---

## Code Review Checklist

Before submitting code, verify:

- [ ] All functions have type hints
- [ ] All public APIs have docstrings
- [ ] No hardcoded secrets or credentials
- [ ] Tests pass: `uv run pytest tests/ -v`
- [ ] Linting passes: `uv run ruff check .`
- [ ] Type checking passes: `uv run mypy .`
- [ ] No new security vulnerabilities introduced
- [ ] Error handling is appropriate
- [ ] Logging is used instead of print statements

---

## Git Workflow

- **Main branch**: `main` (protected)
- **Development branch**: `develop`
- **Feature branches**: `feature/<description>`
- **Bugfix branches**: `fix/<description>`

### Commit Message Format
```
<type>: <short description>

<optional body with details>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

---

## Common Patterns in This Codebase

### Configuration with Dataclasses
```python
@dataclass
class LLMConfig:
    backend: LLMBackend
    model_name: str
    temperature: float = 0.7
```

### Backend Selection with Enums
```python
class LLMBackend(Enum):
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"
```

### Factory Pattern for LLM Initialization
```python
def _initialize_llm(self):
    if self.llm_config.backend == LLMBackend.OLLAMA:
        return OllamaLLM(...)
```

---

## Performance Considerations

- **Embedding caching**: Save/load vectorstore to avoid recomputation
- **Batch processing**: Process multiple documents together
- **Lazy imports**: Import heavy libraries only when needed
- **Connection pooling**: Reuse LLM connections
- **Async operations**: Consider async for I/O-bound operations

---

## Troubleshooting

### Common Issues

**Ollama not responding**:
```bash
# Check if Ollama is running
ollama list
# Start Ollama service
ollama serve
```

**FAISS import errors**:
```bash
# Reinstall faiss-cpu
uv pip install --force-reinstall faiss-cpu
```

**Embedding model download fails**:
```bash
# Manually download model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

---

## References

- [LangChain Documentation](https://python.langchain.com/docs/)
- [FAISS Documentation](https://faiss.ai/)
- [Sentence Transformers](https://www.sbert.net/)
- [Ollama](https://ollama.ai/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
