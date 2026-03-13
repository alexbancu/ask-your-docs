"""One-time ingestion script: load Acme Corp docs into Pinecone."""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.document_loader import load_documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 384
DOCS_DIR = Path(__file__).parent.parent / "resources" / "acme-corp"


def main() -> None:
    """Load markdown documents and upsert into Pinecone."""
    load_dotenv()

    pinecone_api_key = os.getenv("PINECONE_API_KEY", "")
    index_name = os.getenv("PINECONE_INDEX_NAME", "acme-corp-knowledge")

    if not pinecone_api_key:
        logger.error("PINECONE_API_KEY is required")
        sys.exit(1)

    # Initialize Pinecone
    pc = Pinecone(api_key=pinecone_api_key)

    # Delete and recreate index to ensure correct dimensions
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if index_name in existing_indexes:
        logger.info("Deleting existing index '%s'...", index_name)
        pc.delete_index(index_name)
        logger.info("Index deleted")

    logger.info("Creating index '%s' (%d dims, cosine)", index_name, EMBEDDING_DIMENSION)
    pc.create_index(
        name=index_name,
        dimension=EMBEDDING_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )
    logger.info("Index created")

    # Load and chunk documents
    logger.info("Loading documents from %s", DOCS_DIR)
    documents = load_documents(DOCS_DIR)

    if not documents:
        logger.error("No documents loaded")
        sys.exit(1)

    # Initialize embeddings
    logger.info("Initializing embedding model...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # Upsert to Pinecone
    logger.info("Upserting %d chunks to Pinecone...", len(documents))
    PineconeVectorStore.from_documents(
        documents=documents,
        embedding=embeddings,
        index_name=index_name,
        pinecone_api_key=pinecone_api_key,
    )

    logger.info("Ingestion complete!")
    logger.info("  Documents processed: %d", len(set(d.metadata["source_file"] for d in documents)))
    logger.info("  Total chunks: %d", len(documents))


if __name__ == "__main__":
    main()
