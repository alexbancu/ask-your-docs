# Servicegest RAG Assistant

A RAG (Retrieval-Augmented Generation) system that answers questions from PDF documents using local LLMs.

## Quick Start

```bash
# Install dependencies
uv sync

# Start Ollama (if not running)
ollama serve

# Pull the model
ollama pull llama3.1:latest

# Ask a question
uv run python ask.py "How does binary search work?"
```

## Usage

```bash
# Basic usage
python ask.py "What is Big O notation?"

# Rebuild vector store from PDF
python ask.py "Explain quicksort" --rebuild

# Use different model (must be pulled first: ollama pull mistral)
python ask.py "What is a hash table?" --model mistral

# Retrieve more context chunks
python ask.py "Compare BFS and DFS" --chunks 8
```

## Available Models

Pull any of these with `ollama pull <model>`:

| Model | Size | Speed* | Notes |
|-------|------|--------|-------|
| `llama3.1:latest` | 4.9 GB | ~20s | Best quality, default |
| `mistral` | 4.1 GB | ~15s | Good balance |

*Response times on CPU. GPU acceleration significantly improves speed.

## Example Output

```
============================================================
  Servicegest RAG Assistant
============================================================

Loading knowledge base... Done (0.3s)

Question: How does binary search work?

------------------------------------------------------------

Answer:
Binary search works by repeatedly dividing the search interval in half.
You start with a sorted list and guess the middle element. If your guess
is too high, you eliminate the upper half. If too low, you eliminate the
lower half. This continues until you find the element or the interval is
empty.

Sources:
  1. Page 3: "Binary search is a lot faster than simple search..."
  2. Page 5: "With binary search, you guess the middle number..."

[Response time: 2.8s]
```

## Prerequisites

- Python 3.12+
- [Ollama](https://ollama.ai) with llama3.1 model
- PDF in `resources/Grokking Algorithms.pdf`

## How It Works

| Step | Component | Tool | Purpose |
|------|-----------|------|---------|
| 1 | **Document Loader** | PyPDFLoader | Extracts text from PDF pages |
| 2 | **Text Splitter** | RecursiveCharacterTextSplitter | Chunks text (1000 chars, 200 overlap) |
| 3 | **Embeddings** | HuggingFace (MiniLM-L6-v2) | Converts text chunks → vectors |
| 4 | **Vector Store** | FAISS | Stores vectors & finds similar chunks |
| 5 | **LLM** | Ollama (llama3.1) | Generates answer from retrieved context |

```
Query → Embed → Search FAISS → Top K chunks → LLM → Answer + Sources
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| Chunk size | 1000 chars | Text chunk size for splitting |
| Chunk overlap | 200 chars | Overlap between chunks |
| Retrieval k | 4 | Number of chunks to retrieve |
| Model | llama3.1:latest | Ollama model |
| Temperature | 0.7 | LLM creativity |

## Development

```bash
# Run tests
uv run pytest

# Run the demo
uv run python main.py
```
