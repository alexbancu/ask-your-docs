"""Ingestion script: load demo documents into Pinecone namespaces (direct SDKs)."""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pinecone import Pinecone, ServerlessSpec

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.document_loader import list_demos, load_demo_config, load_documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 3072
EMBEDDING_MODEL = "gemini-embedding-001"
BATCH_SIZE = 100


def ingest_demo(
    demo_slug: str,
    index: object,
    client: genai.Client,
) -> None:
    """Ingest a single demo's documents into its Pinecone namespace.

    Args:
        demo_slug: The demo directory name (e.g. 'acme-corp').
        index: Pinecone index object.
        client: Google GenAI client for embeddings.
    """
    docs_dir = Path(__file__).parent.parent / "resources" / demo_slug

    try:
        demo_config = load_demo_config(demo_slug)
    except FileNotFoundError:
        logger.error("No demo.json found for '%s'", demo_slug)
        sys.exit(1)

    logger.info("Ingesting demo '%s' (%s)...", demo_slug, demo_config.name)

    # Clear only this demo's namespace (not the whole index)
    logger.info("Clearing namespace '%s'...", demo_slug)
    try:
        index.delete(delete_all=True, namespace=demo_slug)
    except Exception:
        logger.info("Namespace '%s' doesn't exist yet, skipping clear", demo_slug)

    # Load and chunk documents using demo config
    logger.info("Loading documents from %s", docs_dir)
    documents = load_documents(docs_dir, demo_config=demo_config)

    if not documents:
        logger.error("No documents loaded for demo '%s'", demo_slug)
        sys.exit(1)

    # Embed and upsert in batches
    logger.info("Embedding and upserting %d chunks...", len(documents))
    for batch_start in range(0, len(documents), BATCH_SIZE):
        batch = documents[batch_start : batch_start + BATCH_SIZE]
        texts = [doc.page_content for doc in batch]

        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )

        vectors = []
        for i, (doc, embedding) in enumerate(zip(batch, result.embeddings)):
            source_file = doc.metadata.get("source_file", "unknown")
            vector_id = f"{demo_slug}-{source_file}-{batch_start + i}"
            metadata = {**doc.metadata, "text": doc.page_content}
            vectors.append((vector_id, embedding.values, metadata))

        index.upsert(vectors=vectors, namespace=demo_slug)
        logger.info(
            "Upserted batch %d-%d into namespace '%s'",
            batch_start,
            batch_start + len(batch) - 1,
            demo_slug,
        )

    source_files = {d.metadata["source_file"] for d in documents}
    logger.info(
        "Ingestion complete for '%s': %d documents, %d chunks",
        demo_slug,
        len(source_files),
        len(documents),
    )


def main() -> None:
    """Parse args and ingest demo(s) into Pinecone."""
    parser = argparse.ArgumentParser(description="Ingest demo documents into Pinecone")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", type=str, help="Demo slug to ingest (e.g. acme-corp)")
    group.add_argument("--all", action="store_true", help="Ingest all demos")
    args = parser.parse_args()

    load_dotenv()

    pinecone_api_key = os.getenv("PINECONE_API_KEY", "")
    index_name = os.getenv("PINECONE_INDEX_NAME", "acme-corp-knowledge")
    google_api_key = os.getenv("GOOGLE_API_KEY", "")

    if not pinecone_api_key:
        logger.error("PINECONE_API_KEY is required")
        sys.exit(1)
    if not google_api_key:
        logger.error("GOOGLE_API_KEY is required")
        sys.exit(1)

    # Initialize Pinecone
    pc = Pinecone(api_key=pinecone_api_key)

    # Create index if it doesn't exist
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing_indexes:
        logger.info(
            "Creating index '%s' (%d dims, cosine)", index_name, EMBEDDING_DIMENSION
        )
        pc.create_index(
            name=index_name,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        logger.info("Index created")

    index = pc.Index(index_name)

    # Initialize Google GenAI client
    client = genai.Client(api_key=google_api_key)

    if getattr(args, "all"):
        demos = list_demos()
        if not demos:
            logger.error("No demos found in resources/")
            sys.exit(1)
        for demo in demos:
            ingest_demo(demo.slug, index, client)
    else:
        ingest_demo(args.demo, index, client)

    logger.info("All done!")


if __name__ == "__main__":
    main()
