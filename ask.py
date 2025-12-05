#!/usr/bin/env python3
"""
CLI tool for querying the RAG knowledge base.

Usage:
    python ask.py "How does binary search work?"
    python ask.py "What is Big O notation?" --rebuild
"""

import argparse
import os
import sys
import time
from pathlib import Path

from main import RAGSystem, LLMConfig, LLMBackend
from config import (
    DEFAULT_PDF_PATH,
    DEFAULT_VECTORSTORE_PATH,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_PORT,
    DEFAULT_RETRIEVAL_K,
)


def print_header():
    """Print the CLI header."""
    print()
    print("=" * 60)
    print("  Servicegest RAG Assistant")
    print("=" * 60)
    print()


def print_sources(sources: list):
    """Print source citations."""
    print("\nSources:")
    for i, source in enumerate(sources, 1):
        # Handle both Source dataclass and dict format
        if hasattr(source, "metadata"):
            page = source.metadata.get("page", "?")
            snippet = source.content[:100].replace("\n", " ")
        else:
            page = source["metadata"].get("page", "?")
            snippet = source["content"][:100].replace("\n", " ")
        print(f"  {i}. Page {page}: \"{snippet}...\"")


def load_or_create_vectorstore(
    rag: RAGSystem,
    rebuild: bool = False,
    pdf_path: Path = DEFAULT_PDF_PATH,
    vectorstore_path: Path = DEFAULT_VECTORSTORE_PATH,
) -> float:
    """Load existing vectorstore or create new one. Returns time taken."""
    start = time.time()

    vectorstore_exists = vectorstore_path.exists() and vectorstore_path.is_dir()

    if vectorstore_exists and not rebuild:
        print("Loading knowledge base...", end=" ", flush=True)
        try:
            rag.load_vectorstore(str(vectorstore_path))
            elapsed = time.time() - start
            print(f"Done ({elapsed:.1f}s)")
            return elapsed
        except Exception as e:
            print(f"Failed ({e})")
            print("Rebuilding from PDF...")

    # Create new vectorstore
    if rebuild:
        print("Rebuilding knowledge base from PDF...", end=" ", flush=True)
    else:
        print("Creating knowledge base from PDF...", end=" ", flush=True)

    if not pdf_path.exists():
        print(f"\nError: PDF not found at {pdf_path}")
        print("Please ensure the PDF file exists at the expected location.")
        sys.exit(1)

    rag.load_from_pdf(str(pdf_path))
    rag.save_vectorstore(str(vectorstore_path))

    elapsed = time.time() - start
    print(f"Done ({elapsed:.1f}s)")
    return elapsed


def check_ollama(
    host: str = DEFAULT_OLLAMA_HOST,
    port: int = DEFAULT_OLLAMA_PORT,
) -> bool:
    """Check if Ollama is running at the specified host and port."""
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Query the Grokking Algorithms knowledge base",
        epilog="Example: python ask.py \"How does binary search work?\"",
    )
    parser.add_argument(
        "question",
        help="The question to ask",
    )
    parser.add_argument(
        "--rebuild",
        "-r",
        action="store_true",
        help="Rebuild the vector store from PDF",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=DEFAULT_OLLAMA_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_OLLAMA_MODEL})",
    )
    parser.add_argument(
        "--chunks",
        "-k",
        type=int,
        default=DEFAULT_RETRIEVAL_K,
        help=f"Number of context chunks to retrieve (default: {DEFAULT_RETRIEVAL_K})",
    )

    args = parser.parse_args()

    # Check Ollama
    if not check_ollama():
        print(f"Error: Ollama is not running at {DEFAULT_OLLAMA_HOST}:{DEFAULT_OLLAMA_PORT}")
        print("Start it with: ollama serve")
        sys.exit(1)

    print_header()

    # Initialize RAG system
    config = LLMConfig(
        backend=LLMBackend.OLLAMA,
        model_name=args.model,
    )

    rag = RAGSystem(llm_config=config)

    # Load or create vectorstore
    load_or_create_vectorstore(rag, rebuild=args.rebuild)

    # Query
    print(f"\nQuestion: {args.question}\n")
    print("-" * 60)

    query_start = time.time()
    result = rag.generate_answer(args.question, k=args.chunks)
    query_time = time.time() - query_start

    # Display answer
    print("\nAnswer:")
    print(result.answer)

    # Display sources
    print_sources(result.sources)

    # Timing
    print(f"\n[Response time: {query_time:.1f}s]")
    print()


if __name__ == "__main__":
    main()
