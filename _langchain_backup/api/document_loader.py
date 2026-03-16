"""Markdown document loader with metadata tagging for the Acme Corp knowledge base."""

import logging
import re
from datetime import datetime
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

DOCUMENT_OWNERS: dict[str, str] = {
    "employee-handbook": "HR Team",
    "engineering-runbook": "Platform Engineering",
    "onboarding-guide": "People Ops",
    "product-docs": "Product Management",
    "security-policy": "InfoSec Team",
}

STALE_THRESHOLD_DAYS = 180


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


def _parse_last_updated(content: str) -> str | None:
    """Extract the 'Last updated: ...' date string from markdown content.

    Args:
        content: Raw markdown text.

    Returns:
        Date string (e.g. 'January 15, 2025') or None if not found.
    """
    match = re.search(r"Last updated:\s*(.+)", content)
    if match:
        return match.group(1).strip()
    return None


def _is_stale(last_updated: str | None) -> bool:
    """Check if a document is stale (older than STALE_THRESHOLD_DAYS).

    Args:
        last_updated: Date string like 'January 15, 2025'.

    Returns:
        True if the date is more than STALE_THRESHOLD_DAYS ago, or if unparseable.
    """
    if not last_updated:
        return True
    try:
        date = datetime.strptime(last_updated, "%B %d, %Y")
        return (datetime.now() - date).days > STALE_THRESHOLD_DAYS
    except ValueError:
        return True


def load_full_document(directory: str | Path, slug: str) -> dict | None:
    """Read a single markdown file and return its content with metadata.

    Args:
        directory: Path to directory containing markdown files.
        slug: Filename stem (e.g. 'employee-handbook').

    Returns:
        Dict with name, slug, document_type, content, owner, last_updated,
        is_stale, and section_count. None if file not found.
    """
    directory = Path(directory)
    md_file = directory / f"{slug}.md"

    if not md_file.exists():
        return None

    content = md_file.read_text(encoding="utf-8")
    last_updated = _parse_last_updated(content)
    sections = re.findall(r"^##\s+\d+\.", content, re.MULTILINE)

    return {
        "name": _filename_to_document_name(slug),
        "slug": slug,
        "document_type": FILENAME_TO_TYPE.get(slug, "general"),
        "content": content,
        "owner": DOCUMENT_OWNERS.get(slug, "Unknown"),
        "last_updated": last_updated,
        "is_stale": _is_stale(last_updated),
        "section_count": len(sections),
    }
