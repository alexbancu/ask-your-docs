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


# Configuration
PDF_PATH = "resources/Grokking Algorithms.pdf"
VECTORSTORE_PATH = "vectorstore"
DEFAULT_MODEL = "llama3.1:latest"


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
        page = source["metadata"].get("page", "?")
        snippet = source["content"][:100].replace("\n", " ")
        print(f"  {i}. Page {page}: \"{snippet}...\"")


def load_or_create_vectorstore(rag: RAGSystem, rebuild: bool = False) -> float:
    """Load existing vectorstore or create new one. Returns time taken."""
    start = time.time()

    vectorstore_exists = os.path.exists(VECTORSTORE_PATH) and os.path.isdir(VECTORSTORE_PATH)

    if vectorstore_exists and not rebuild:
        print("Loading knowledge base...", end=" ", flush=True)
        try:
            rag.load_vectorstore(VECTORSTORE_PATH)
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

    if not os.path.exists(PDF_PATH):
        print(f"\nError: PDF not found at {PDF_PATH}")
        sys.exit(1)

    rag.load_from_pdf(PDF_PATH)
    rag.save_vectorstore(VECTORSTORE_PATH)

    elapsed = time.time() - start
    print(f"Done ({elapsed:.1f}s)")
    return elapsed


def check_ollama():
    """Check if Ollama is running."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 11434))
        sock.close()
        return result == 0
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Query the Grokking Algorithms knowledge base",
        epilog="Example: python ask.py \"How does binary search work?\""
    )
    parser.add_argument(
        "question",
        help="The question to ask"
    )
    parser.add_argument(
        "--rebuild", "-r",
        action="store_true",
        help="Rebuild the vector store from PDF"
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--chunks", "-k",
        type=int,
        default=4,
        help="Number of context chunks to retrieve (default: 4)"
    )

    args = parser.parse_args()

    # Check Ollama
    if not check_ollama():
        print("Error: Ollama is not running.")
        print("Start it with: ollama serve")
        sys.exit(1)

    print_header()

    # Initialize RAG system
    config = LLMConfig(
        backend=LLMBackend.OLLAMA,
        model_name=args.model,
        temperature=0.7,
        max_tokens=512
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
    print(result["answer"])

    # Display sources
    print_sources(result["sources"])

    # Timing
    print(f"\n[Response time: {query_time:.1f}s]")
    print()


if __name__ == "__main__":
    main()
