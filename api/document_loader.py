"""Markdown document loader with metadata tagging for the Acme Corp knowledge base."""

import logging
import re
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

FILENAME_TO_TYPE: dict[str, str] = {
    "employee-handbook": "hr",
    "engineering-runbook": "engineering",
    "onboarding-guide": "onboarding",
    "product-docs": "product",
    "security-policy": "security",
}


def _filename_to_document_name(filename: str) -> str:
    """Convert a filename stem to a human-readable document name.

    Args:
        filename: File stem (without extension).

    Returns:
        Human-readable name.
    """
    return filename.replace("-", " ").title()


def _count_heading_level(text: str) -> int:
    """Find the current section number from markdown headings in text.

    Args:
        text: Text chunk to analyze.

    Returns:
        Last section number found, or 0 if none.
    """
    sections = re.findall(r"^##\s+(\d+)\.", text, re.MULTILINE)
    if sections:
        return int(sections[-1])
    return 0


def load_documents(directory: str | Path) -> list[Document]:
    """Load and chunk all markdown files from a directory with metadata.

    Args:
        directory: Path to directory containing markdown files.

    Returns:
        List of Document objects with enriched metadata.

    Raises:
        FileNotFoundError: If directory does not exist.
    """
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )

    all_documents: list[Document] = []
    md_files = sorted(directory.glob("*.md"))

    if not md_files:
        logger.warning("No markdown files found in %s", directory)
        return []

    for md_file in md_files:
        stem = md_file.stem
        doc_name = _filename_to_document_name(stem)
        doc_type = FILENAME_TO_TYPE.get(stem, "general")

        content = md_file.read_text(encoding="utf-8")
        chunks = splitter.split_text(content)

        for chunk in chunks:
            section_num = _count_heading_level(chunk)
            doc = Document(
                page_content=chunk,
                metadata={
                    "source_document": doc_name,
                    "document_type": doc_type,
                    "section_number": section_num,
                    "source_file": md_file.name,
                },
            )
            all_documents.append(doc)

        logger.info(
            "Loaded %s: %d chunks (type=%s)", doc_name, len(chunks), doc_type
        )

    logger.info("Total: %d chunks from %d documents", len(all_documents), len(md_files))
    return all_documents
